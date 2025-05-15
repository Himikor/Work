from flask import Flask, render_template, url_for, redirect, request, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

app.secret_key = 'TEST_SECRET_KEY'

# Модель пользователя
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    password = db.Column('password', db.String(), nullable=False)
    email = db.Column(db.String(20), nullable=True)
    balance = db.Column(db.Float(), nullable=True) 

    def set_password(self, secret):
        self.password = generate_password_hash(secret)

    def check_password(self, secret):
        return check_password_hash(self.password, secret)

admin = User(username="admin")
admin.set_password("admin")
admin.balance = 9999
admin.email = ""

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(200), nullable=True)


    



@app.route('/')
def index():
    products = Product.query.all()
    return render_template("index.html", products=products)

@app.route('/auth', methods=['POST'])
def Auth():
    return render_template("auth.html")

@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']
    confirm_password = request.form['confirm_password']
    # Проверка на совпадение паролей
    if password != confirm_password:
        return redirect(url_for('index'))

    # Хеширование пароля
    hashed_password = generate_password_hash(password)

    # Проверка на уникальность имени пользователя или email
    if User.query.filter_by(username=username).first():
        print('Username already exists!', 'error')
        return redirect(url_for('index'))
    if User.query.filter_by(email=email).first():
        print('Email already registered!', 'error')
        return redirect(url_for('index'))

    

    return redirect(url_for('index'))

@app.context_processor
def inject_user():
    # Проверка, есть ли пользователь в сессии
    user_authenticated = session.get('logged_in') or None
    user_avatar_url = None
    if user_authenticated:
            user = User.query.get(session['logged_in'])
            user_avatar_url = '/static/images/def_icon.png'
            return dict(user_authenticated=user_authenticated, user_avatar_url=user_avatar_url, user=user)
    return {'user': None}

@app.route('/login', methods=['GET', 'POST'])
def loginIn():
    username = request.form['username']
    password = request.form['password']
    user = User.query.filter_by(username=username).first()
    if user and username == "admin" and user.check_password(password):
        session['logged_in'] = True             # проверка через метод
        session['is_admin'] = True
        return redirect(url_for('admin_panel'))
    if user and user.check_password(password):
        session['logged_in'] = True             # проверка через метод
        return redirect(url_for('index'))
    
    return "Invalid credentials", 401


@app.route('/logout', methods=['GET'])
def logout():
    # Очистка всех данных из сессии
    session.clear()
    # Перенаправление на главную страницу
    return redirect(url_for('index'))


@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if not session.get('logged_in') and session.get("is_admin"):
        return "ABORTED", 401
    users = User.query.all()
    if request.method == "POST":
        # Получаем данные из формы
        name = request.form.get("name")
        description = request.form.get("description")
        price = request.form.get("price")
        quantity = request.form.get("quantity")
        image_url = request.form.get("image_url")

        # Создаем новый товар
        new_product = Product(
            name=name,
            description=description,
            price=float(price),
            quantity=int(quantity),
            image_url=image_url
        )
        db.session.add(new_product)
        db.session.commit()

        return redirect(url_for("index"))
    return render_template("admin.html", users=users)

@app.route('/admin/update_balance', methods=['POST'])
def update_balance():
    if 'logged_in' not in session or not session.get('is_admin'):
        print("У вас нет прав для выполнения этого действия.", "error")
        return redirect(url_for('index'))

    user_id = request.form.get('user_id')
    new_balance = request.form.get('new_balance')

    try:
        new_balance = float(new_balance)
    except ValueError:
        print("Неверный формат баланса.", "error")
        return redirect(url_for('admin_panel'))

    user = User.query.get(user_id)
    if not user:
        print("Пользователь не найден.", "error")
        return redirect(url_for('admin_panel'))

    # Обновляем баланс пользователя
    user.balance = new_balance
    db.session.commit()

    return redirect(url_for('index'))


@app.route('/buy', methods=['POST'])
def buy_product():
    product_id = request.form.get('product_id')
    # Логика для обработки покупки
    product = Product.query.get(product_id)
    
    user = User.query.get(session['logged_in'])

    if user.balance < product.price:
        return "Недостаточно средств на балансе", 400

    if product and product.quantity > 0:
        user.balance -= product.price
        product.quantity -= 1
    # Сохраняем изменения в базе данных
    db.session.commit()
    
    return redirect(url_for('index'))


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        db.session.add(admin)
        try:
            db.session.commit()
        
        except IntegrityError:
            db.session.rollback()

        except Exception as e:
            db.session.rollback() 

    app.run(debug=True)
    

