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

