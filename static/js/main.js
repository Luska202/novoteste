// Menu mobile e scroll navbar
document.addEventListener('DOMContentLoaded', function() {
    const navToggle = document.getElementById('nav-toggle');
    const navMenu = document.getElementById('nav-menu');
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }

    // Navbar muda ao rolar
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    });

    // Inicializar setas de scroll
    document.querySelectorAll('.horizontal-scroll').forEach(container => {
        adicionarSetasScroll(container);
    });

    // Carregar estado dos favoritos
    carregarEstadoFavoritos();
});

// Template para cards - ajustado para episódios irem direto ao player
window.cardTemplate = function(item) {
    let link;
    if (item.temporada !== null && item.episodio !== null) {
        // É um episódio específico
        link = `/play/${item.id}`;
    } else if (item.tipo === 'serie' && item.serie_nome) {
        // É uma série (agrupada)
        link = `/serie/${encodeURIComponent(item.serie_nome)}`;
    } else {
        // É filme, TV, rádio
        link = `/play/${item.id}`;
    }
    return `
        <div class="card" onclick="window.location.href='${link}'">
            <img src="${item.logo || '/static/images/placeholder.png'}" alt="${item.nome}" onerror="this.src='/static/images/placeholder.png'">
            <div class="card-body">
                <h3 class="card-title">${item.nome}</h3>
                <a href="${link}" class="btn-small" onclick="event.stopPropagation();">Assistir</a>
                <button class="favorito-btn" data-id="${item.id}" onclick="event.stopPropagation();"><i class="fas fa-heart"></i></button>
            </div>
        </div>
    `;
};

// Carregar estado dos favoritos
function carregarEstadoFavoritos() {
    fetch('/api/favoritos')
        .then(res => res.json())
        .then(favoritos => {
            const favoritosIds = new Set(favoritos.map(f => f.id));
            document.querySelectorAll('.favorito-btn').forEach(btn => {
                const id = parseInt(btn.dataset.id);
                if (favoritosIds.has(id)) {
                    btn.classList.add('favorito-ativo');
                } else {
                    btn.classList.remove('favorito-ativo');
                }
            });
        })
        .catch(err => console.error('Erro ao carregar favoritos:', err));
}

// Favoritar
document.addEventListener('click', function(e) {
    const btn = e.target.closest('.favorito-btn');
    if (!btn) return;

    e.preventDefault();
    e.stopPropagation();

    const id = btn.dataset.id;
    fetch(`/favoritar/${id}`, { method: 'POST' })
        .then(res => {
            if (!res.ok) throw new Error('Erro ao favoritar');
            return res.json();
        })
        .then(data => {
            if (data.status === 'adicionado') {
                btn.classList.add('favorito-ativo');
            } else {
                btn.classList.remove('favorito-ativo');
            }
            // Atualiza outros botões (opcional)
            carregarEstadoFavoritos();
        })
        .catch(err => {
            console.error('Erro:', err);
            alert('Falha ao favoritar. Tente novamente.');
        });
});

// Função para pesquisa com Enter - agora aceita callback
window.setupSearch = function(inputId, btnId, callback) {
    const input = document.getElementById(inputId);
    const btn = document.getElementById(btnId);
    if (!input) return;

    const performSearch = () => {
        const term = input.value.trim();
        if (term !== '') {
            callback(term);
        }
    };

    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') performSearch();
    });
    if (btn) btn.addEventListener('click', performSearch);
};

// Adicionar setas de scroll
function adicionarSetasScroll(container) {
    if (container.parentNode.classList.contains('scroll-container')) return;

    const wrapper = document.createElement('div');
    wrapper.className = 'scroll-container';
    container.parentNode.insertBefore(wrapper, container);
    wrapper.appendChild(container);

    const leftArrow = document.createElement('button');
    leftArrow.className = 'scroll-arrow left';
    leftArrow.innerHTML = '&#10094;';
    leftArrow.addEventListener('click', () => {
        container.scrollBy({ left: -400, behavior: 'smooth' });
    });

    const rightArrow = document.createElement('button');
    rightArrow.className = 'scroll-arrow right';
    rightArrow.innerHTML = '&#10095;';
    rightArrow.addEventListener('click', () => {
        container.scrollBy({ left: 400, behavior: 'smooth' });
    });

    wrapper.appendChild(leftArrow);
    wrapper.appendChild(rightArrow);
}

