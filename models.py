from database import db
from datetime import datetime

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha = db.Column(db.String(200), nullable=False)
    favoritos = db.relationship('Favorito', backref='usuario', lazy=True)
    progressos = db.relationship('Progresso', backref='usuario', lazy=True)

class Canal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200))
    url = db.Column(db.String(500))
    logo = db.Column(db.String(500))
    grupo = db.Column(db.String(100))
    tvg_id = db.Column(db.String(100))
    tipo = db.Column(db.String(20))  # 'tv', 'serie', 'filme', 'radio'
    serie_nome = db.Column(db.String(200))
    temporada = db.Column(db.Integer)
    episodio = db.Column(db.Integer)
    categoria = db.Column(db.String(100))

    def serialize(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'url': self.url,
            'logo': self.logo,
            'tipo': self.tipo,
            'categoria': self.categoria,
            'temporada': self.temporada,
            'episodio': self.episodio,
            'serie_nome': self.serie_nome
        }

class Favorito(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    canal_id = db.Column(db.Integer, db.ForeignKey('canal.id'))
    tipo = db.Column(db.String(20))

class Progresso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    canal_id = db.Column(db.Integer, db.ForeignKey('canal.id'))
    tempo = db.Column(db.Integer)
    duracao = db.Column(db.Integer)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow)