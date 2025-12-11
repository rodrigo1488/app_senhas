// Teste simples de cliques
console.log('=== TESTE DE CLIQUES INICIADO ===');

let clicks = 0;

document.addEventListener('click', function(e) {
    console.log('Clique detectado em:', e.target.tagName);
    
    // Só conta cliques no body ou div
    if (e.target.tagName === 'BODY' || e.target.tagName === 'DIV') {
        clicks++;
        console.log('Clique válido! Total:', clicks);
        
        if (clicks >= 5) {
            console.log('5 cliques! Redirecionando...');
            window.location.href = '/setores';
        }
    }
});

console.log('Teste de cliques ativado!'); 