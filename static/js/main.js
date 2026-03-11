// Função de pesquisa
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            const term = this.value.toLowerCase();
            const cards = document.querySelectorAll('.grid .card');
            cards.forEach(card => {
                const nome = card.dataset.nome || card.querySelector('h3')?.textContent.toLowerCase();
                if (nome && nome.includes(term)) {
                    card.style.display = 'block';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    // Favoritar
    document.querySelectorAll('.favorito').forEach(btn => {
        btn.addEventListener('click', function() {
            const canalId = this.dataset.id;
            fetch(`/favoritar/${canalId}`, { method: 'POST' })
                .then(res => res.json())
                .then(data => {
                    if (data.status === 'adicionado') {
                        this.textContent = '⭐ Remover';
                    } else {
                        this.textContent = '⭐';
                    }
                });
        });
    });
});