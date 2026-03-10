// Funções globais, como favoritar
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('favorite-btn')) {
        const btn = e.target;
        const id = btn.dataset.id;
        const tipo = btn.dataset.tipo;
        const acao = btn.dataset.action || 'add'; // se não tiver action, assume add
        fetch('/favoritar', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({tipo: tipo, item_id: parseInt(id), acao: acao})
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') {
                if (acao === 'add') {
                    btn.textContent = '❤️';
                    btn.dataset.action = 'remove';
                } else {
                    btn.textContent = '🤍';
                    btn.dataset.action = 'add';
                    // Se estiver na página de favoritos, remove o card
                    if (window.location.pathname === '/favoritos') {
                        btn.closest('.favorito-card').remove();
                    }
                }
            }
        });
    }
});