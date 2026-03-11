// Menu mobile
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }
});

// Template para cards com link para detalhe
window.cardTemplate = function(item, tipo) {
    let link = '';
    if (tipo === 'filme') {
        link = `/filme/${item.id}`;
    } else if (tipo === 'serie') {
        link = `/serie/${encodeURIComponent(item.serie_nome || item.nome)}`;
    } else {
        link = `/play/${item.id}`; // para TV, rádio, etc.
    }
    return `
        <div class="card" onclick="window.location.href='${link}'">
            <img src="${item.logo || '/static/images/placeholder.png'}" alt="${item.nome}" onerror="this.src='/static/images/placeholder.png'">
            <div class="card-body">
                <h3 class="card-title">${item.nome}</h3>
                <a href="${link}" class="btn btn-small" onclick="event.stopPropagation();">Assistir</a>
                <button class="favorito-btn" data-id="${item.id}" onclick="event.stopPropagation();"><i class="fas fa-heart"></i></button>
            </div>
        </div>
    `;
};

// Favoritar (delegação de eventos)
document.addEventListener('click', function(e) {
    if (e.target.closest('.favorito-btn')) {
        e.preventDefault();
        e.stopPropagation();
        const btn = e.target.closest('.favorito-btn');
        const id = btn.dataset.id;
        fetch(`/favoritar/${id}`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'adicionado') {
                    btn.classList.add('favorito-ativo');
                } else {
                    btn.classList.remove('favorito-ativo');
                }
            });
    }
});

// Função para pesquisa com Enter - redireciona
window.setupSearch = function(inputId, btnId) {
    const input = document.getElementById(inputId);
    const btn = document.getElementById(btnId);
    if (!input) return;

    const performSearch = () => {
        const term = input.value.trim();
        if (term !== '') {
            window.location.href = `/busca?q=${encodeURIComponent(term)}`;
        }
    };

    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    if (btn) {
        btn.addEventListener('click', performSearch);
    }
};