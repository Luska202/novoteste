import os
import re
from models import Canal, Serie, Episodio, Filme

def parse_m3u_line(line):
    # Extrai atributos da linha #EXTINF
    attrs = {}
    # Padrão para encontrar atributos entre aspas
    pattern = r'(\w+)=["\']([^"\']*)["\']'
    matches = re.findall(pattern, line)
    for key, value in matches:
        attrs[key] = value
    # Extrai o nome após a vírgula
    if ',' in line:
        nome = line.split(',', 1)[1].strip()
        attrs['name'] = nome
    return attrs

def load_m3u_to_db(app, db):
    m3u_path = os.path.join(app.root_path, 'lista.m3u')
    if not os.path.exists(m3u_path):
        print("Arquivo lista.m3u não encontrado. Coloque na pasta raiz.")
        return

    with open(m3u_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    i = 0
    total = len(lines)
    while i < total:
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            # Linha de informação
            info_line = line
            attrs = parse_m3u_line(info_line)
            # Próxima linha deve ser a URL
            i += 1
            if i < total:
                url_line = lines[i].strip()
                if url_line and not url_line.startswith('#'):
                    # Determinar tipo
                    group_title = attrs.get('group-title', '')
                    tvg_id = attrs.get('tvg-id', '')
                    tvg_name = attrs.get('tvg-name', attrs.get('name', ''))
                    tvg_logo = attrs.get('tvg-logo', '')

                    # Classificar
                    if tvg_id:  # tem tvg-id, provavelmente TV
                        tipo = 'tv'
                        canal = Canal(
                            nome=tvg_name,
                            logo=tvg_logo,
                            url=url_line,
                            tvg_id=tvg_id,
                            group_title=group_title,
                            tipo=tipo
                        )
                        db.session.add(canal)
                    elif 'Série' in group_title or 'Series' in group_title:
                        # É uma série
                        # Extrair categoria após o hífen
                        categoria = ''
                        if ' - ' in group_title:
                            parts = group_title.split(' - ', 1)
                            if len(parts) > 1:
                                categoria = parts[1].strip()
                        # Verificar se é um episódio (contém SxxExx)
                        nome_ep = tvg_name
                        # Padrão para temporada e episódio: S01E02, S1E2, etc.
                        padrao = r'S(\d+)E(\d+)'
                        match = re.search(padrao, nome_ep, re.IGNORECASE)
                        if match:
                            temporada = int(match.group(1))
                            episodio = int(match.group(2))
                            # Nome do episódio (remover o código SxxExx)
                            nome_ep_limpo = re.sub(padrao, '', nome_ep, flags=re.IGNORECASE).strip()
                            if not nome_ep_limpo:
                                nome_ep_limpo = nome_ep
                            # Procurar série pelo nome base (sem o código)
                            nome_serie = re.sub(padrao, '', nome_ep, flags=re.IGNORECASE).strip()
                            # Ou usar o tvg-name? Pode ser que o nome da série esteja antes do código
                            # Exemplo: "Nome da Série S01E01"
                            # Vamos tentar extrair nome da série removendo o padrão
                            # Mas pode ser que o nome completo esteja no tvg-name
                            # Vamos criar ou encontrar série
                            serie = Serie.query.filter_by(nome=nome_serie).first()
                            if not serie:
                                serie = Serie(nome=nome_serie, logo=tvg_logo, categoria=categoria)
                                db.session.add(serie)
                                db.session.flush()  # para obter id
                            # Adicionar episódio
                            ep = Episodio(
                                serie_id=serie.id,
                                temporada=temporada,
                                episodio=episodio,
                                nome=nome_ep_limpo,
                                url=url_line
                            )
                            db.session.add(ep)
                        else:
                            # Pode ser um item de série sem episódio? Talvez a série em si não tenha URL
                            # Ignoramos?
                            pass
                    elif 'Filme' in group_title or 'Movie' in group_title:
                        categoria = ''
                        if ' - ' in group_title:
                            parts = group_title.split(' - ', 1)
                            if len(parts) > 1:
                                categoria = parts[1].strip()
                        filme = Filme(
                            nome=tvg_name,
                            logo=tvg_logo,
                            categoria=categoria,
                            url=url_line
                        )
                        db.session.add(filme)
                    else:
                        # Se não identificou, talvez seja TV também?
                        # Pode ser TV sem tvg-id? Vamos colocar como TV genérico
                        canal = Canal(
                            nome=tvg_name,
                            logo=tvg_logo,
                            url=url_line,
                            tvg_id='',
                            group_title=group_title,
                            tipo='tv'
                        )
                        db.session.add(canal)
        i += 1

    db.session.commit()
    print("Banco de dados populado com sucesso!")