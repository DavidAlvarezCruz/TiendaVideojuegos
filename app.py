from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User   
from models import db, Game, Order, OrderItem
from flask_migrate import Migrate


app = Flask(__name__)
migrate = Migrate(app, db)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['JWT_SECRET_KEY'] = 'david3010'  

db.init_app(app)
jwt = JWTManager(app)


#########################################################
#                                                       #
#                       USUARIOS                        #
#                                                       #
#########################################################


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
    return 'La API está corriendo'

# Login
@app.route('/api/users/login', methods=['POST'])
def login():
    data = request.get_json(force=True)

    if not data or not all(k in data for k in ('username', 'password')):
        return jsonify({"msg": "Datos incompletos"}), 400

    user = User.query.filter_by(username=data['username']).first()
    if user and check_password_hash(user.password, data['password']):
        token = create_access_token(
            identity=str(user.id),   
            additional_claims={"is_admin": user.is_admin}
        )
        return jsonify(access_token=token)
    return jsonify({"msg": "Credenciales inválidas"}), 401

# Obtener usuario
@app.route('/api/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    current_user_id = int(get_jwt_identity())   
    claims = get_jwt()
    is_admin = claims.get("is_admin", False)

    if current_user_id != user_id and not is_admin:
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
    current_user_id = int(get_jwt_identity())  
    claims = get_jwt()
    is_admin = claims.get("is_admin", False)

    if current_user_id != user_id and not is_admin:
        return jsonify({"msg": "No autorizado"}), 403

    user = User.query.get_or_404(user_id)
    data = request.get_json(force=True)

    if "email" in data:
        user.email = data["email"]
    if "password" in data:
        user.password = generate_password_hash(data["password"])

    db.session.commit()
    return jsonify({"msg": "Usuario actualizado"})

#Eliminar usuario

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    current_user_id = get_jwt_identity() 
    current_user = User.query.get(current_user_id)

    if not current_user or not current_user.is_admin:
        return jsonify({"msg": "No autorizado"}), 403

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({"msg": "Usuario eliminado"})

#########################################################
#                                                       #
#                       JUEGOS                          #
#                                                       #
#########################################################

# Crear un nuevo juego
@app.route('/api/games', methods=['POST'])
@jwt_required() 
def create_game():
    data = request.get_json(force=True)
    
    required_fields = ['title', 'price']
    if not data or not all(field in data for field in required_fields):
        return jsonify({"msg": "Faltan campos obligatorios: title y price"}), 400

    new_game = Game(
        title=data['title'],
        description=data.get('description', ''),  
        price=float(data['price']),
        stock=int(data.get('stock', 0))           
    )

    db.session.add(new_game)
    db.session.commit()

    return jsonify({
        "msg": "Videojuego creado",
        "game": {
            "id": new_game.id,
            "title": new_game.title,
            "description": new_game.description,
            "price": new_game.price,
            "stock": new_game.stock
        }
    }), 201


# Visualizar un juego específico
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


#Actualizar el juego

@app.route('/api/games/<int:game_id>', methods=['PUT'])
@jwt_required() 
def update_game(game_id):
    game = Game.query.get_or_404(game_id)   
    data = request.get_json(force=True)

    if 'title' in data:
        game.title = data['title']
    if 'description' in data:
        game.description = data['description']
    if 'price' in data:
        game.price = float(data['price'])
    if 'stock' in data:
        game.stock = int(data['stock'])

    db.session.commit()

    return jsonify({
        "msg": "Videojuego actualizado",
        "game": {
            "id": game.id,
            "title": game.title,
            "description": game.description,
            "price": game.price,
            "stock": game.stock
        }
    })

#Eliminar el juego

@app.route('/api/games/<int:game_id>', methods=['DELETE'])
@jwt_required()  
def delete_game(game_id):
    game = Game.query.get_or_404(game_id)

    db.session.delete(game)
    db.session.commit()

    return jsonify({"msg": f"Videojuego '{game.title}' eliminado con éxito"})


#########################################################
#                                                       #
#                       PEDIDOS                         #
#                                                       #
#########################################################


# Crear el pedido

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.get_json(force=True)

    if not data or "items" not in data or "user_id" not in data:
        return jsonify({"msg": "El pedido debe contener user_id e items"}), 400

    user_id = data["user_id"]

    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": f"Usuario con id {user_id} no existe"}), 404

    new_order = Order(user_id=user_id)
    db.session.add(new_order)
    db.session.flush()  

    for item in data["items"]:
        game = Game.query.get(item["game_id"])
        if not game:
            return jsonify({"msg": f"Juego con id {item['game_id']} no existe"}), 404
        if game.stock < item["quantity"]:
            return jsonify({"msg": f"No hay suficiente stock para {game.title}"}), 400

        game.stock -= item["quantity"]

        order_item = OrderItem(order_id=new_order.id, game_id=game.id, quantity=item["quantity"])
        db.session.add(order_item)

    db.session.commit()

    return jsonify({"msg": "Pedido creado", "order_id": new_order.id}), 201



# Visualizar un pedido 

@app.route('/api/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    order = Order.query.get_or_404(order_id)
    return jsonify({
        "id": order.id,
        "user_id": order.user_id,
        "created_at": order.created_at,
        "status": order.status,
        "items": [
            {"game_id": item.game_id, "quantity": item.quantity}
            for item in order.items
        ]
    })


# Actualizar el pedido

@app.route('/api/orders/<int:order_id>', methods=['PUT'])
@jwt_required()
def update_order(order_id):
    order = Order.query.get_or_404(order_id)
    data = request.get_json(force=True)

    if "status" in data:
        order.status = data["status"]

    db.session.commit()
    return jsonify({"msg": "Pedido actualizado", "status": order.status})

# Eliminar el pedido

@app.route('/api/orders/<int:order_id>', methods=['DELETE'])
@jwt_required()
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    return jsonify({"msg": f"Pedido {order.id} eliminado"})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)