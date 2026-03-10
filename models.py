from app import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)

class Canal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200))
    logo = db.Column(db.String(500))
    url = db.Column(db.String(500))
    tvg_id = db.Column(db.String(100))
    group_title = db.Column(db.String(200))
    tipo = db.Column(db.String(20))  # 'tv'

class Serie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200))
    logo = db.Column(db.String(500))
    categoria = db.Column(db.String(200))
    # Não tem URL própria, mas episódios têm

class Episodio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    serie_id = db.Column(db.Integer, db.ForeignKey('serie.id'))
    temporada = db.Column(db.Integer)
    episodio = db.Column(db.Integer)
    nome = db.Column(db.String(200))
    url = db.Column(db.String(500))
    duracao = db.Column(db.Integer)  # opcional

class Filme(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200))
    logo = db.Column(db.String(500))
    categoria = db.Column(db.String(200))
    url = db.Column(db.String(500))

class Favorito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    item_id = db.Column(db.Integer)  # ID do item na tabela correspondente
    tipo = db.Column(db.String(20))  # 'tv', 'serie', 'filme'

class Progresso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    item_id = db.Column(db.Integer)
    tipo = db.Column(db.String(20))
    temporada = db.Column(db.Integer, nullable=True)
    episodio = db.Column(db.Integer, nullable=True)
    tempo_assistido = db.Column(db.Integer, default=0)
    duracao_total = db.Column(db.Integer, default=0)