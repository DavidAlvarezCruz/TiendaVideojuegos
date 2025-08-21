from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User   # asegúrate de tener tu modelo definido
from models import db, Game, Order, OrderItem


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['JWT_SECRET_KEY'] = 'david3010'  # cámbialo en producción

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
            identity=str(user.id),   # ahora es un string
            additional_claims={"is_admin": user.is_admin}
        )
        return jsonify(access_token=token)
    return jsonify({"msg": "Credenciales inválidas"}), 401

# Obtener usuario
@app.route('/api/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    current_user_id = int(get_jwt_identity())   # ahora sí, string → int
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
    current_user_id = int(get_jwt_identity())   # identity es un string con el id
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
    current_user_id = get_jwt_identity()  # esto es un número o string
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
        description=data.get('description', ''),  # opcional
        price=float(data['price']),
        stock=int(data.get('stock', 0))           # opcional, default 0
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
@jwt_required()  # opcional, si quieres que solo usuarios logueados puedan modificar
def update_game(game_id):
    game = Game.query.get_or_404(game_id)   # Busca el juego o devuelve 404
    data = request.get_json(force=True)

    # Actualizar solo los campos que vengan en el JSON
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
@jwt_required()  # opcional, si solo usuarios logueados o admins pueden borrar
def delete_game(game_id):
    game = Game.query.get_or_404(game_id)

    db.session.delete(game)
    db.session.commit()

    return jsonify({"msg": f"Videojuego '{game.title}' eliminado con éxito"})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)