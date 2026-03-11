// Menu mobile
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }

    // Inicializar setas de scroll para cada container horizontal
    document.querySelectorAll('.horizontal-scroll').forEach(container => {
        adicionarSetasScroll(container);
    });
});

// Template para cards
window.cardTemplate = function(item) {
    const link = item.tipo === 'serie' && item.serie_nome 
        ? `/serie/${encodeURIComponent(item.serie_nome)}`
        : `/play/${item.id}`;
    return `
        <div class="card" onclick="window.location.href='${link}'">
            <img src="${item.logo || '/static/images/placeholder.png'}" alt="${item.nome}" onerror="this.src='/static/images/placeholder.png'">
            <div class="card-body">
                <h3 class="card-title">${item.nome}</h3>
                <a href="${link}" class="btn btn-small" onclick="event.stopPropagation();">Assistir</a>
                <button class="favorito-btn" data-id="${item.id}" onclick="event.stopPropagation();">
                    <i class="fas fa-heart"></i>
                </button>
            </div>
        </div>
    `;
};

// Favoritar (delegação de eventos)
document.addEventListener('click', function(e) {
    const btn = e.target.closest('.favorito-btn');
    if (btn) {
        e.preventDefault();
        e.stopPropagation();
        const id = btn.dataset.id;
        // Mostrar feedback visual (opcional)
        btn.disabled = true;
        fetch(`/favoritar/${id}`, { method: 'POST' })
            .then(res => res.json())
            .then(data => {
                btn.disabled = false;
                if (data.status === 'adicionado') {
                    btn.classList.add('favorito-ativo');
                } else if (data.status === 'removido') {
                    btn.classList.remove('favorito-ativo');
                } else {
                    console.error('Resposta inesperada:', data);
                }
            })
            .catch(err => {
                btn.disabled = false;
                console.error('Erro ao favoritar:', err);
            });
    }
});

// Função para pesquisa com Enter
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

// Função para adicionar setas de scroll
function adicionarSetasScroll(container) {
    // Evita adicionar múltiplas vezes
    if (container.parentNode.classList.contains('scroll-container')) return;

    const wrapper = document.createElement('div');
    wrapper.className = 'scroll-container';
    container.parentNode.insertBefore(wrapper, container);
    wrapper.appendChild(container);

    const leftArrow = document.createElement('button');
    leftArrow.className = 'scroll-arrow left';
    leftArrow.innerHTML = '&#10094;';
    leftArrow.addEventListener('click', () => {
        container.scrollBy({ left: -300, behavior: 'smooth' });
    });

    const rightArrow = document.createElement('button');
    rightArrow.className = 'scroll-arrow right';
    rightArrow.innerHTML = '&#10095;';
    rightArrow.addEventListener('click', () => {
        container.scrollBy({ left: 300, behavior: 'smooth' });
    });

    wrapper.appendChild(leftArrow);
    wrapper.appendChild(rightArrow);
}