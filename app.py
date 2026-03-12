import os
import json
import logging
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, Response
from database import init_db, db
from models import Usuario, Canal, Favorito, Progresso
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import func, desc
import requests

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Troque em produção
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

init_db(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- Funções auxiliares para carregar JSON ----------
def carregar_json_no_banco():
    if Canal.query.first() is not None:
        logger.info("Banco já contém dados. Nenhuma carga realizada.")
        return

    json_dir = 'm3u'
    json_path = os.path.join(json_dir, 'lista.json')
    if not os.path.exists(json_path):
        logger.warning(f"Arquivo {json_path} não encontrado.")
        return

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            dados = json.load(f)
    except Exception as e:
        logger.error(f"Erro ao ler JSON: {e}")
        return

    if not isinstance(dados, list):
        logger.error("Formato JSON inválido: esperava uma lista.")
        return

    for item in dados:
        nome = item.get('nome', '')
        logo = item.get('logo', '')
        tipo_original = item.get('tipo', '')
        categoria = item.get('categoria', '')
        temporada = item.get('temporada')
        episodio = item.get('episodio')
        url = item.get('url', '')

        if tipo_original.lower() == 'radio':
            tipo = 'radio'
        elif tipo_original.lower() == 'series':
            tipo = 'serie'
        elif tipo_original.lower() == 'filmes':
            tipo = 'filme'
        else:
            tipo = 'tv'

        canal = Canal(
            nome=nome,
            url=url,
            logo=logo,
            grupo='',
            tvg_id='',
            tipo=tipo,
            categoria=categoria,
            temporada=temporada if temporada is not None else None,
            episodio=episodio if episodio is not None else None
        )
        if tipo == 'serie':
            import re
            match = re.search(r'S(\d+)E(\d+)', nome, re.IGNORECASE)
            if match:
                canal.serie_nome = re.sub(r'S\d+E\d+', '', nome, flags=re.IGNORECASE).strip()
            else:
                canal.serie_nome = nome
        db.session.add(canal)

    db.session.commit()
    logger.info(f"{len(dados)} itens carregados do JSON.")

# ---------- Rotas principais ----------
@app.route('/')
def index():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario and check_password_hash(usuario.senha, senha):
            session['usuario_id'] = usuario.id
            return redirect(url_for('index'))
        return render_template('login.html', erro='Email ou senha inválidos')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        if Usuario.query.filter_by(email=email).first():
            return render_template('register.html', erro='Email já cadastrado')
        hash_senha = generate_password_hash(senha)
        usuario = Usuario(nome=nome, email=email, senha=hash_senha)
        db.session.add(usuario)
        db.session.commit()
        session['usuario_id'] = usuario.id
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('usuario_id', None)
    return redirect(url_for('login'))

@app.route('/tv')
def tv():
    return render_template('tv.html')

@app.route('/series')
def series():
    return render_template('series.html')

@app.route('/filmes')
def filmes():
    return render_template('filmes.html')

@app.route('/radio')
def radio():
    return render_template('radio.html')

@app.route('/serie/<nome>')
def serie_detalhe(nome):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    episodios = Canal.query.filter_by(tipo='serie', serie_nome=nome).order_by(
        Canal.temporada, Canal.episodio).all()
    if not episodios:
        return redirect(url_for('series'))
    temporadas = {}
    for ep in episodios:
        temp = ep.temporada
        if temp not in temporadas:
            temporadas[temp] = []
        temporadas[temp].append(ep)
    return render_template('series-detalhe.html', serie_nome=nome, temporadas=temporadas)

@app.route('/filme/<int:id>')
def filme_detalhe(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    filme = Canal.query.get_or_404(id)
    return render_template('filme-detalhe.html', filme=filme)

@app.route('/play/<int:id>')
def play(id):
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    canal = Canal.query.get_or_404(id)
    proximo = None
    if canal.tipo == 'serie' and canal.serie_nome and canal.temporada is not None and canal.episodio is not None:
        # Busca próximo episódio na mesma série
        proximo = Canal.query.filter(
            Canal.tipo=='serie',
            Canal.serie_nome == canal.serie_nome,
            ((Canal.temporada == canal.temporada) & (Canal.episodio > canal.episodio)) |
            ((Canal.temporada == canal.temporada + 1) & (Canal.episodio == 1))
        ).order_by(Canal.temporada, Canal.episodio).first()
    return render_template('player.html', canal=canal, proximo_episodio=proximo)

@app.route('/favoritos')
def favoritos():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario_id = session['usuario_id']
    favs = Favorito.query.filter_by(usuario_id=usuario_id).all()
    return render_template('favoritos.html', favoritos=favs)

@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario = Usuario.query.get(session['usuario_id'])
    return render_template('perfil.html', usuario=usuario)

@app.route('/busca')
def busca():
    termo = request.args.get('q', '')
    return render_template('resultados.html', termo=termo)



# ---------- API ----------
def filtrar_adultos(query):
    """Exclui itens com categoria 'Adultos'."""
    return query.filter((Canal.categoria != 'Adultos') | (Canal.categoria.is_(None)))

def get_random_items(tipo, limite=15):
    from sqlalchemy.sql.expression import func
    query = Canal.query.filter_by(tipo=tipo)
    query = filtrar_adultos(query)
    return query.order_by(func.random()).limit(limite).all()

def get_mais_assistidos_global(limite=5):
    """
    Retorna os itens mais assistidos globalmente (todos os usuários).
    Para filmes: conta progressos por canal.
    Para séries: agrupa por série (serie_nome) e conta progressos de todos os episódios,
                 e retorna o episódio mais recente da série (para link direto).
    """
    # Contagem de progressos por item (filmes e episódios)
    progress_counts = db.session.query(
        Progresso.canal_id,
        func.count(Progresso.id).label('total')
    ).group_by(Progresso.canal_id).subquery()

    # Join com Canal para obter dados
    query = db.session.query(Canal, progress_counts.c.total).join(
        progress_counts, Canal.id == progress_counts.c.canal_id
    )

    # Separar filmes e séries
    filmes = query.filter(Canal.tipo == 'filme').order_by(desc(progress_counts.c.total)).all()
    series_raw = query.filter(Canal.tipo == 'serie').all()

    # Para séries, agrupar por serie_nome
    series_map = {}
    for canal, total in series_raw:
        if canal.serie_nome not in series_map:
            series_map[canal.serie_nome] = {
                'total': 0,
                'latest': canal  # vamos pegar o último episódio (maior id) para representar
            }
        series_map[canal.serie_nome]['total'] += total
        # Manter o episódio com maior id (último adicionado)
        if canal.id > series_map[canal.serie_nome]['latest'].id:
            series_map[canal.serie_nome]['latest'] = canal

    # Converter para lista ordenada
    series_list = []
    for nome, data in series_map.items():
        series_list.append((data['latest'], data['total']))

    # Ordenar séries por total decrescente
    series_list.sort(key=lambda x: x[1], reverse=True)

    # Combinar filmes e séries e ordenar globalmente
    combined = [(canal, total) for canal, total in filmes] + series_list
    combined.sort(key=lambda x: x[1], reverse=True)

    # Retornar apenas os canais (objetos) no limite
    return [c[0] for c in combined[:limite]]

@app.route('/api/mais-assistidos')
def api_mais_assistidos():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    itens = get_mais_assistidos_global(5)
    return jsonify([c.serialize() for c in itens])

def get_recentemente_assistidos(usuario_id, limite=15):
    """
    Retorna os itens assistidos recentemente, agrupando séries (apenas o último episódio de cada série).
    """
    # Subconsulta para séries
    subquery_series = db.session.query(
        Progresso.canal_id,
        Progresso.data_atualizacao,
        func.row_number().over(
            partition_by=Canal.serie_nome,
            order_by=desc(Progresso.data_atualizacao)
        ).label('rn')
    ).join(Canal, Progresso.canal_id == Canal.id).filter(
        Progresso.usuario_id == usuario_id,
        Canal.tipo == 'serie'
    ).subquery()

    series_recentes = db.session.query(Progresso).join(
        subquery_series,
        (Progresso.canal_id == subquery_series.c.canal_id) &
        (subquery_series.c.rn == 1)
    ).all()

    # Filmes e outros (sem agrupamento)
    outros = Progresso.query.join(Canal).filter(
        Progresso.usuario_id == usuario_id,
        Canal.tipo != 'serie'
    ).order_by(desc(Progresso.data_atualizacao)).all()

    todos = series_recentes + outros
    todos.sort(key=lambda p: p.data_atualizacao, reverse=True)
    return [p.canal for p in todos[:limite] if p.canal]

@app.route('/api/destaque')
def api_destaque():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    itens = get_mais_assistidos(5)
    return jsonify([c.serialize() for c in itens])

@app.route('/api/inicio')
def api_inicio():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    usuario_id = session['usuario_id']
    filmes_rec = [c.serialize() for c in get_random_items('filme', 15)]
    series_rec = [c.serialize() for c in get_random_items('serie', 15)]
    recentes = [c.serialize() for c in get_recentemente_assistidos(usuario_id, 15)]
    return jsonify({
        'filmes_recomendados': filmes_rec,
        'series_recomendadas': series_rec,
        'assistido_recentemente': recentes
    })

@app.route('/api/filmes/categoria/<categoria>')
def api_filmes_categoria(categoria):
    query = Canal.query.filter_by(tipo='filme', categoria=categoria)
    query = filtrar_adultos(query)
    filmes = query.limit(15).all()
    return jsonify([f.serialize() for f in filmes])

@app.route('/api/filmes/lancamento')
def api_filmes_lancamento():
    query = Canal.query.filter_by(tipo='filme')
    query = filtrar_adultos(query)
    filmes = query.order_by(Canal.id.desc()).limit(15).all()
    return jsonify([f.serialize() for f in filmes])

@app.route('/api/filmes/lista')
def api_filmes_lista():
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 10
    query = Canal.query.filter_by(tipo='filme')
    query = filtrar_adultos(query)
    filmes = query.order_by(Canal.nome).paginate(page=pagina, per_page=por_pagina, error_out=False)
    return jsonify({
        'itens': [f.serialize() for f in filmes.items],
        'total': filmes.total,
        'pagina': pagina,
        'total_paginas': filmes.pages
    })

@app.route('/api/series/categoria/<categoria>')
def api_series_categoria(categoria):
    from sqlalchemy import func
    subquery = db.session.query(Canal.serie_nome, db.func.min(Canal.id).label('id')).filter(
        Canal.tipo=='serie', Canal.categoria==categoria).group_by(Canal.serie_nome).subquery()
    query = db.session.query(Canal).join(subquery, Canal.id == subquery.c.id)
    query = filtrar_adultos(query)
    series = query.limit(15).all()
    return jsonify([s.serialize() for s in series])

@app.route('/api/series/lancamento')
def api_series_lancamento():
    from sqlalchemy import func
    subquery = db.session.query(Canal.serie_nome, db.func.min(Canal.id).label('id')).filter_by(tipo='serie').group_by(Canal.serie_nome).subquery()
    query = db.session.query(Canal).join(subquery, Canal.id == subquery.c.id)
    query = filtrar_adultos(query)
    series = query.order_by(Canal.id.desc()).limit(15).all()
    return jsonify([s.serialize() for s in series])

@app.route('/api/series/lista')
def api_series_lista():
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 10
    from sqlalchemy import func
    subquery = db.session.query(Canal.serie_nome, db.func.min(Canal.id).label('id')).filter_by(tipo='serie').group_by(Canal.serie_nome).subquery()
    query = db.session.query(Canal).join(subquery, Canal.id == subquery.c.id)
    query = filtrar_adultos(query)
    series = query.order_by(Canal.serie_nome).paginate(page=pagina, per_page=por_pagina, error_out=False)
    return jsonify({
        'itens': [s.serialize() for s in series.items],
        'total': series.total,
        'pagina': pagina,
        'total_paginas': series.pages
    })

@app.route('/api/tv/lista')
def api_tv_lista():
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 10
    query = Canal.query.filter_by(tipo='tv')
    query = filtrar_adultos(query)
    canais = query.order_by(Canal.nome).paginate(page=pagina, per_page=por_pagina, error_out=False)
    return jsonify({
        'itens': [c.serialize() for c in canais.items],
        'total': canais.total,
        'pagina': pagina,
        'total_paginas': canais.pages
    })

@app.route('/api/radio/lista')
def api_radio_lista():
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 10
    query = Canal.query.filter_by(tipo='radio')
    query = filtrar_adultos(query)
    radios = query.order_by(Canal.nome).paginate(page=pagina, per_page=por_pagina, error_out=False)
    return jsonify({
        'itens': [r.serialize() for r in radios.items],
        'total': radios.total,
        'pagina': pagina,
        'total_paginas': radios.pages
    })

@app.route('/api/busca')
def api_busca():
    termo = request.args.get('q', '').strip()
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 20
    if not termo:
        return jsonify({'itens': [], 'total': 0, 'pagina': 1, 'total_paginas': 1})
    
    # Busca geral
    query = Canal.query.filter(Canal.nome.ilike(f'%{termo}%'))
    query = filtrar_adultos(query)
    
    # Precisamos agrupar séries para não repetir episódios
    # Vamos fazer duas consultas: uma para séries (agrupadas) e outra para os demais tipos
    from sqlalchemy import func
    
    # Subconsulta para séries: pegar o menor ID de cada série que corresponde ao termo
    subquery_series = db.session.query(
        Canal.serie_nome,
        func.min(Canal.id).label('id')
    ).filter(
        Canal.tipo == 'serie',
        Canal.nome.ilike(f'%{termo}%')
    ).group_by(Canal.serie_nome).subquery()
    
    series = db.session.query(Canal).join(
        subquery_series, Canal.id == subquery_series.c.id
    ).all()
    
    # Outros tipos (filme, tv, radio) - busca normal
    outros = Canal.query.filter(
        Canal.tipo.in_(['filme', 'tv', 'radio']),
        Canal.nome.ilike(f'%{termo}%')
    ).all()
    
    # Combina e ordena
    resultados = series + outros
    # Ordenar por nome
    resultados.sort(key=lambda x: x.nome)
    
    # Paginação manual simples
    total = len(resultados)
    inicio = (pagina - 1) * por_pagina
    fim = inicio + por_pagina
    itens_pagina = resultados[inicio:fim]
    
    return jsonify({
        'itens': [c.serialize() for c in itens_pagina],
        'total': total,
        'pagina': pagina,
        'total_paginas': (total + por_pagina - 1) // por_pagina
    })

def serialize_canal(canal):
    return {
        'id': canal.id,
        'nome': canal.nome,
        'url': canal.url,
        'logo': canal.logo,
        'tipo': canal.tipo,
        'categoria': canal.categoria,
        'temporada': canal.temporada,
        'episodio': canal.episodio,
        'serie_nome': canal.serie_nome
    }
Canal.serialize = serialize_canal

# ---------- Rotas para categorias ----------
@app.route('/api/filmes/categorias')
def api_filmes_categorias():
    categorias = db.session.query(Canal.categoria).filter_by(tipo='filme').distinct().all()
    return jsonify([c[0] for c in categorias if c[0]])

@app.route('/api/series/categorias')
def api_series_categorias():
    categorias = db.session.query(Canal.categoria).filter_by(tipo='serie').distinct().all()
    return jsonify([c[0] for c in categorias if c[0]])

@app.route('/api/filmes/categoria/<categoria>/lista')
def api_filmes_categoria_lista(categoria):
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 20
    query = Canal.query.filter_by(tipo='filme', categoria=categoria)
    total = query.count()
    filmes = query.order_by(Canal.nome).paginate(page=pagina, per_page=por_pagina, error_out=False)
    return jsonify({
        'itens': [f.serialize() for f in filmes.items],
        'total': total,
        'pagina': pagina,
        'total_paginas': filmes.pages
    })

@app.route('/api/series/categoria/<categoria>/lista')
def api_series_categoria_lista(categoria):
    pagina = int(request.args.get('pagina', 1))
    por_pagina = 20
    from sqlalchemy import func
    subquery = db.session.query(Canal.serie_nome, func.min(Canal.id).label('id')).filter(
        Canal.tipo=='serie', Canal.categoria==categoria).group_by(Canal.serie_nome).subquery()
    query = db.session.query(Canal).join(subquery, Canal.id == subquery.c.id)
    total = query.count()
    series = query.order_by(Canal.serie_nome).paginate(page=pagina, per_page=por_pagina, error_out=False)
    return jsonify({
        'itens': [s.serialize() for s in series.items],
        'total': total,
        'pagina': pagina,
        'total_paginas': series.pages
    })

# ---------- Favoritos ----------
@app.route('/favoritar/<int:canal_id>', methods=['POST'])
def favoritar(canal_id):
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    usuario_id = session['usuario_id']
    existe = Favorito.query.filter_by(usuario_id=usuario_id, canal_id=canal_id).first()
    if existe:
        db.session.delete(existe)
        db.session.commit()
        return jsonify({'status': 'removido'})
    else:
        canal = Canal.query.get(canal_id)
        if not canal:
            return jsonify({'erro': 'Canal não encontrado'}), 404
        fav = Favorito(usuario_id=usuario_id, canal_id=canal_id, tipo=canal.tipo)
        db.session.add(fav)
        db.session.commit()
        return jsonify({'status': 'adicionado'})

@app.route('/api/favoritos')
def api_favoritos():
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    usuario_id = session['usuario_id']
    favs = Favorito.query.filter_by(usuario_id=usuario_id).all()
    return jsonify([f.canal.serialize() for f in favs if f.canal])

# ---------- Progresso ----------
@app.route('/progresso/<int:canal_id>', methods=['POST'])
def salvar_progresso(canal_id):
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    data = request.get_json()
    tempo = data.get('tempo')
    duracao = data.get('duracao')
    usuario_id = session['usuario_id']
    progresso = Progresso.query.filter_by(usuario_id=usuario_id, canal_id=canal_id).first()
    if progresso:
        progresso.tempo = tempo
        progresso.duracao = duracao
        progresso.data_atualizacao = datetime.utcnow()
    else:
        progresso = Progresso(usuario_id=usuario_id, canal_id=canal_id, tempo=tempo, duracao=duracao)
        db.session.add(progresso)
    db.session.commit()
    return jsonify({'status': 'ok'})

@app.route('/progresso/<int:canal_id>', methods=['GET'])
def obter_progresso(canal_id):
    if 'usuario_id' not in session:
        return jsonify({'erro': 'Não autenticado'}), 401
    usuario_id = session['usuario_id']
    progresso = Progresso.query.filter_by(usuario_id=usuario_id, canal_id=canal_id).first()
    if progresso:
        return jsonify({'tempo': progresso.tempo, 'duracao': progresso.duracao})
    return jsonify({'tempo': 0, 'duracao': 0})

# ---------- Proxy ----------
@app.route('/proxy')
def proxy():
    url = request.args.get('url')
    if not url:
        return 'URL não fornecida', 400
    headers = {}
    if 'Range' in request.headers:
        headers['Range'] = request.headers.get('Range')
    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=10)
        excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
        headers = [(name, value) for name, value in resp.raw.headers.items() if name.lower() not in excluded_headers]
        return Response(resp.iter_content(chunk_size=8192), status=resp.status_code, headers=headers)
    except Exception as e:
        return f'Erro no proxy: {str(e)}', 500

if __name__ == '__main__':
    with app.app_context():
        carregar_json_no_banco()
    app.run(debug=True)