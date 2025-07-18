from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from models import db, User, Game, Order, OrderItem
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['JWT_SECRET_KEY'] = 'david3010'  # Cambia esto en producción

db.init_app(app)
jwt = JWTManager(app)

    
# Registro
@app.route('/api/users/register', methods=['POST'])
def register():
    data = request.get_json(force=True)

    if not data or not all(k in data for k in ('username', 'email', 'password')):
        return jsonify({"msg": "Datos incompletos"}), 400

    hashed_pw = generate_password_hash(data['password'])
    new_user = User(username=data['username'], email=data['email'], password=hashed_pw)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"msg": "Usuario registrado"}), 201

@app.route('/')
def index():
    return 'La API está corriendo '

# Login
@app.route('/api/users/login', methods=['POST'])
def login():
    data = request.get_json(force=True)

    if not data or not all(k in data for k in ('username', 'password')):
        return jsonify({"msg": "Datos incompletos"}), 400

    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        token = create_access_token(identity={'id': user.id, 'is_admin': user.is_admin})
        return jsonify(access_token=token)
    return jsonify({"msg": "Credenciales inválidas"}), 401

# Obtener usuario
@app.route('/api/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    user_data = get_jwt_identity()
    if user_data['id'] != user_id and not user_data['is_admin']:
        return jsonify({"msg": "No autorizado"}), 403

    user = User.query.get_or_404(user_id)
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin
    })

# Actualizar usuario
@app.route('/api/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    user_data = get_jwt_identity()
    if user_data['id'] != user_id and not user_data['is_admin']:
        return jsonify({"msg": "No autorizado"}), 403

    user = User.query.get_or_404(user_id)
    data = request.get_json(force=True)
    user.email = data.get('email', user.email)
    if 'password' in data:
        user.password = generate_password_hash(data['password'])
    db.session.commit()
    return jsonify({"msg": "Usuario actualizado"})

# Eliminar usuario
@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    user_data = get_jwt_identity()
    if not user_data['is_admin']:
        return jsonify({"msg": "No autorizado"}), 403

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"msg": "Usuario eliminado"})

@app.route('/api/games/<int:game_id>', methods=['GET'])
def get_game(game_id):
    game = Game.query.get_or_404(game_id)
    return jsonify({
        "id": game.id,
        "title": game.title,
        "description": game.description,
        "price": game.price,
        "stock": game.stock
    })

@app.route('/api/games/<int:game_id>', methods=['PUT'])
@jwt_required()
def update_game(game_id):
    user = get_jwt_identity()
    if not user['is_admin']:
        return jsonify({"msg": "No autorizado"}), 403

    game = Game.query.get_or_404(game_id)
    data = request.get_json(force=True)
    game.title = data.get('title', game.title)
    game.description = data.get('description', game.description)
    game.price = data.get('price', game.price)
    game.stock = data.get('stock', game.stock)
    db.session.commit()
    return jsonify({"msg": "Juego actualizado"})

@app.route('/api/games/<int:game_id>', methods=['DELETE'])
@jwt_required()
def delete_game(game_id):
    user = get_jwt_identity()
    if not user['is_admin']:
        return jsonify({"msg": "No autorizado"}), 403

    game = Game.query.get_or_404(game_id)
    db.session.delete(game)
    db.session.commit()
    return jsonify({"msg": "Juego eliminado"})


@app.route('/api/orders', methods=['POST'])
@jwt_required()
def create_order():
    user_data = get_jwt_identity()
    data = request.get_json(force=True)
    items = data.get('items', [])

    if not items:
        return jsonify({"msg": "El pedido debe tener al menos un juego"}), 400

    total = 0
    order = Order(user_id=user_data['id'], total_price=0)
    db.session.add(order)
    db.session.flush()  # para obtener el ID sin commit aún

    for item in items:
        game = Game.query.get(item['game_id'])
        if not game or game.stock < item['quantity']:
            return jsonify({"msg": f"Stock insuficiente para {game.title if game else 'Juego'}"}), 400

        game.stock -= item['quantity']
        total += game.price * item['quantity']
        order_item = OrderItem(order_id=order.id, game_id=game.id, quantity=item['quantity'], price=game.price)
        db.session.add(order_item)

    order.total_price = total
    db.session.commit()
    return jsonify({"msg": "Pedido creado", "order_id": order.id}), 201

@app.route('/api/orders/user/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user_orders(user_id):
    user_data = get_jwt_identity()
    if user_data['id'] != user_id and not user_data['is_admin']:
        return jsonify({"msg": "No autorizado"}), 403

    orders = Order.query.filter_by(user_id=user_id).all()
    return jsonify([
        {"id": o.id, "total_price": o.total_price, "created_at": o.created_at}
        for o in orders
    ])

@app.route('/api/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    user_data = get_jwt_identity()
    order = Order.query.get_or_404(order_id)
    if order.user_id != user_data['id'] and not user_data['is_admin']:
        return jsonify({"msg": "No autorizado"}), 403

    return jsonify({
        "id": order.id,
        "total_price": order.total_price,
        "created_at": order.created_at,
        "items": [
            {"game_id": i.game_id, "quantity": i.quantity, "price": i.price}
            for i in order.items
        ]
    })

@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
@jwt_required()
def delete_order(order_id):
    user_data = get_jwt_identity()
    order = Order.query.get_or_404(order_id)
    if order.user_id != user_data['id'] and not user_data['is_admin']:
        return jsonify({"msg": "No autorizado"}), 403

    db.session.delete(order)
    db.session.commit()
    return jsonify({"msg": "Pedido cancelado"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

