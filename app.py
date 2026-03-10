import os
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import init_db, load_m3u_to_db

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua-chave-secreta-aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Importar modelos após criar db
from models import User, Canal, Serie, Episodio, Filme, Favorito, Progresso

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Inicializar banco de dados e carregar M3U na primeira execução
with app.app_context():
    db.create_all()
    # Verifica se já existem canais, se não, carrega do arquivo m3u
    if Canal.query.count() == 0 and Serie.query.count() == 0 and Filme.query.count() == 0:
        load_m3u_to_db(app, db)  # função definida em database.py

# Rotas de autenticação
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.senha_hash, senha):
            login_user(user)
            return redirect(url_for('index'))
        flash('Email ou senha inválidos')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        if User.query.filter_by(email=email).first():
            flash('Email já cadastrado')
        else:
            novo_user = User(nome=nome, email=email, senha_hash=generate_password_hash(senha))
            db.session.add(novo_user)
            db.session.commit()
            login_user(novo_user)
            return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Rotas principais
@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/tv')
@login_required
def tv():
    canais = Canal.query.filter_by(tipo='tv').all()
    return render_template('tv.html', canais=canais)

@app.route('/series')
@login_required
def series():
    # Lista de séries (agrupadas por nome) - precisamos da tabela Serie
    series = Serie.query.all()
    return render_template('series.html', series=series)

@app.route('/serie/<int:serie_id>')
@login_required
def serie_detalhe(serie_id):
    serie = Serie.query.get_or_404(serie_id)
    episodios = Episodio.query.filter_by(serie_id=serie_id).order_by(Episodio.temporada, Episodio.episodio).all()
    # Agrupar por temporada
    temporadas = {}
    for ep in episodios:
        if ep.temporada not in temporadas:
            temporadas[ep.temporada] = []
        temporadas[ep.temporada].append(ep)
    return render_template('serie-detalhe.html', serie=serie, temporadas=temporadas)

@app.route('/filmes')
@login_required
def filmes():
    filmes = Filme.query.all()
    return render_template('filmes.html', filmes=filmes)

@app.route('/filme/<int:filme_id>')
@login_required
def filme_detalhe(filme_id):
    filme = Filme.query.get_or_404(filme_id)
    return render_template('filme-detalhe.html', filme=filme)

@app.route('/favoritos')
@login_required
def favoritos():
    favoritos = Favorito.query.filter_by(user_id=current_user.id).all()
    # Precisamos buscar os objetos reais
    items = []
    for fav in favoritos:
        if fav.tipo == 'serie':
            item = Serie.query.get(fav.item_id)
        elif fav.tipo == 'filme':
            item = Filme.query.get(fav.item_id)
        elif fav.tipo == 'tv':
            item = Canal.query.get(fav.item_id)
        else:
            continue
        if item:
            items.append({'tipo': fav.tipo, 'item': item})
    return render_template('favoritos.html', items=items)

@app.route('/perfil')
@login_required
def perfil():
    return render_template('perfil.html', user=current_user)

# API para favoritar/desfavoritar
@app.route('/favoritar', methods=['POST'])
@login_required
def favoritar():
    data = request.get_json()
    tipo = data['tipo']
    item_id = data['item_id']
    acao = data['acao']  # 'add' ou 'remove'
    if acao == 'add':
        fav = Favorito(user_id=current_user.id, item_id=item_id, tipo=tipo)
        db.session.add(fav)
        db.session.commit()
        return jsonify({'status': 'ok'})
    elif acao == 'remove':
        Favorito.query.filter_by(user_id=current_user.id, item_id=item_id, tipo=tipo).delete()
        db.session.commit()
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'erro'}), 400

# API para salvar progresso
@app.route('/progresso', methods=['POST'])
@login_required
def progresso():
    data = request.get_json()
    tipo = data['tipo']
    item_id = data['item_id']
    tempo = data['tempo']  # em segundos
    duracao = data.get('duracao', 0)
    temporada = data.get('temporada')
    episodio = data.get('episodio')
    # Verifica se já existe progresso
    prog = Progresso.query.filter_by(user_id=current_user.id, item_id=item_id, tipo=tipo,
                                     temporada=temporada, episodio=episodio).first()
    if prog:
        prog.tempo_assistido = tempo
        prog.duracao_total = duracao
    else:
        prog = Progresso(user_id=current_user.id, item_id=item_id, tipo=tipo,
                         temporada=temporada, episodio=episodio, tempo_assistido=tempo, duracao_total=duracao)
        db.session.add(prog)
    db.session.commit()
    return jsonify({'status': 'ok'})

# API para obter progresso
@app.route('/progresso/<tipo>/<int:item_id>')
@login_required
def get_progresso(tipo, item_id):
    temporada = request.args.get('temporada', type=int)
    episodio = request.args.get('episodio', type=int)
    prog = Progresso.query.filter_by(user_id=current_user.id, item_id=item_id, tipo=tipo,
                                     temporada=temporada, episodio=episodio).first()
    if prog:
        return jsonify({'tempo': prog.tempo_assistido, 'duracao': prog.duracao_total})
    return jsonify({'tempo': 0, 'duracao': 0})

if __name__ == '__main__':
    app.run(debug=True)