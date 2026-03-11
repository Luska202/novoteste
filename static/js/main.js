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

// Funções para carregar dados via API (serão usadas nas páginas específicas)
window.loadItems = function(url, containerId, templateFn, loadMoreBtnId, page = 1) {
    fetch(`${url}?pagina=${page}`)
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById(containerId);
            data.itens.forEach(item => {
                container.insertAdjacentHTML('beforeend', templateFn(item));
            });
            if (loadMoreBtnId) {
                const btn = document.getElementById(loadMoreBtnId);
                if (data.pagina < data.total_paginas) {
                    btn.style.display = 'block';
                    btn.dataset.page = data.pagina + 1;
                } else {
                    btn.style.display = 'none';
                }
            }
        });
};

// Template para cards (exemplo)
window.cardTemplate = function(item) {
    return `
        <div class="card" data-id="${item.id}">
            <img src="${item.logo || '/static/images/placeholder.png'}" alt="${item.nome}" onerror="this.src='/static/images/placeholder.png'">
            <div class="card-body">
                <h3 class="card-title">${item.nome}</h3>
                <a href="/play/${item.id}" class="btn btn-small">Assistir</a>
                <button class="favorito-btn" data-id="${item.id}"><i class="fas fa-heart"></i></button>
            </div>
        </div>
    `;
};

// Favoritar (delegação de eventos)
document.addEventListener('click', function(e) {
    if (e.target.closest('.favorito-btn')) {
        e.preventDefault();
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