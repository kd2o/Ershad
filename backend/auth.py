# login / logout / register / forgot password / reset password 
from flask import *
from backend import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required, current_user


auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = db.db.users.find_one({'email': email})
        if user and check_password_hash(user['password'], password):
            login_user(user)
            return redirect(url_for('main.home'))
        else :
            flash('the password or the email is wrong')
        return redirect(url_for('auth.login'))
    

@auth.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user['role'] != 'admin':
        flash('get out pls ur not admin')
        return redirect(url_for('main.home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        if db.db.users.find_one({'email': email}):
            flash('this email is already used')
            return redirect(url_for('add_user'))
        
        db.db.users.insert_one({
            'email': email,
            'password': generate_password_hash(password),
            'role': role
        })
        flash('user added successfully')
        return redirect(url_for('main.home'))
    return render_template('add_user.html')
