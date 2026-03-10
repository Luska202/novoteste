from flask import Flask, request, Response, render_template, jsonify, abort
import requests
import os
import re

app = Flask(__name__)

# Configuração: limite de 100MB para uploads
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB

# Manipuladores de erro globais
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Rota não encontrada'}), 404

@app.errorhandler(413)
def request_entity_too_large(e):
    return jsonify({'error': 'Arquivo muito grande. O limite é 100MB.'}), 413

@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({'error': f'Erro interno: {str(e)}'}), 500

def parse_extinf(line):
    """
    Extrai atributos e título de uma linha #EXTINF.
    Formato esperado: #EXTINF:<duração> [atributos],<título>
    Atributos são pares chave="valor" (podem ter espaços).
    Retorna um dicionário com os atributos e a chave 'name' para o título.
    """
    line = line[8:].strip()  # Remove '#EXTINF:'
    parts = line.split(',', 1)
    if len(parts) != 2:
        return {'name': line.strip()}
    attr_part, title = parts
    title = title.strip()
    duration_part = attr_part.split(' ', 1)
    duration = duration_part[0].strip()
    rest = duration_part[1] if len(duration_part) > 1 else ''
    attrs = {'duration': duration}
    pattern = r'(\w+)=["\']([^"\']*)["\']'
    matches = re.findall(pattern, rest)
    for key, value in matches:
        attrs[key] = value
    attrs['name'] = title
    return attrs

def parse_m3u(content):
    lines = content.splitlines()
    channels = []
    current_attrs = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#EXTINF:'):
            current_attrs = parse_extinf(line)
        elif line.startswith('#'):
            continue
        else:
            url = line
            if current_attrs:
                channel = current_attrs.copy()
                channel['url'] = url
                channels.append(channel)
                current_attrs = {}
            else:
                channels.append({'name': 'Canal sem nome', 'url': url})
    return channels

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Arquivo vazio'}), 400
    try:
        content = file.read().decode('utf-8')
        channels = parse_m3u(content)
        return jsonify({'channels': channels})
    except UnicodeDecodeError:
        return jsonify({'error': 'Arquivo não está em UTF-8. Tente salvar como UTF-8.'}), 400
    except Exception as e:
        return jsonify({'error': f'Erro ao processar: {str(e)}'}), 500

@app.route('/proxy')
def proxy():
    url = request.args.get('url')
    if not url:
        abort(400, description='Parâmetro "url" é obrigatório')
    headers = {}
    if 'Range' in request.headers:
        headers['Range'] = request.headers.get('Range')
    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=10)
        excluded_headers = ['content-encoding', 'content-length',
                            'transfer-encoding', 'connection']
        headers = [(name, value) for name, value in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        return Response(resp.iter_content(chunk_size=8192),
                        status=resp.status_code,
                        headers=headers)
    except requests.exceptions.Timeout:
        abort(504, description='Timeout ao acessar o stream')
    except requests.exceptions.ConnectionError:
        abort(502, description='Erro de conexão com o servidor de origem')
    except Exception as e:
        abort(500, description=f'Erro no proxy: {str(e)}')

if __name__ == '__main__':
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)