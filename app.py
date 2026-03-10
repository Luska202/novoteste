from flask import Flask, request, Response, render_template, abort
import requests
import os

app = Flask(__name__)

def parse_m3u(content):
    """Analisa o conteúdo de um arquivo M3U e retorna uma lista de canais."""
    lines = content.splitlines()
    channels = []
    current = {}
    for line in lines:
        line = line.strip()
        if line.startswith('#EXTINF:'):
            # Formato: #EXTINF:-1 tvg-id="" tvg-logo="" group-title="",Nome do Canal
            parts = line.split(',', 1)
            if len(parts) > 1:
                name = parts[1].strip()
            else:
                name = "Canal sem nome"
            current['name'] = name
        elif line and not line.startswith('#'):
            # Linha com a URL
            current['url'] = line
            if 'name' in current and 'url' in current:
                channels.append(current.copy())
            current = {}
    return channels

@app.route('/')
def index():
    """Renderiza a página principal."""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    """Recebe o arquivo M3U, faz o parsing e retorna a lista de canais em JSON."""
    if 'file' not in request.files:
        return {'error': 'Nenhum arquivo enviado'}, 400
    file = request.files['file']
    if file.filename == '':
        return {'error': 'Arquivo vazio'}, 400
    try:
        content = file.read().decode('utf-8')
        channels = parse_m3u(content)
        return {'channels': channels}
    except Exception as e:
        return {'error': str(e)}, 500

@app.route('/proxy')
def proxy():
    """
    Proxy para os streams.
    Recebe a URL real do stream via parâmetro 'url' e faz o encaminhamento,
    mantendo os cabeçalhos necessários (como Range) para suporte a busca.
    """
    url = request.args.get('url')
    if not url:
        abort(400, 'Parâmetro "url" é obrigatório')

    # Repassa cabeçalhos como Range para permitir seek no vídeo
    headers = {}
    if 'Range' in request.headers:
        headers['Range'] = request.headers.get('Range')

    try:
        resp = requests.get(url, headers=headers, stream=True)
        # Remove cabeçalhos problemáticos
        excluded_headers = ['content-encoding', 'content-length',
                            'transfer-encoding', 'connection']
        headers = [(name, value) for name, value in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]

        # Retorna o conteúdo em streaming
        return Response(resp.iter_content(chunk_size=8192),
                        status=resp.status_code,
                        headers=headers)
    except Exception as e:
        abort(500, f'Erro ao acessar o stream: {str(e)}')

if __name__ == '__main__':
    # Cria a pasta templates se não existir (para o index.html)
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)