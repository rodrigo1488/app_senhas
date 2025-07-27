// Versão simplificada do sistema de 5 cliques consecutivos
console.log('=== SISTEMA DE 5 CLIQUES SIMPLIFICADO CARREGADO ===');

let clickCount = 0;
let clickTimer = null;

// Função simples para detectar cliques
function handleClick(event) {
    console.log('Clique detectado!');
    
    // Ignora cliques em elementos interativos
    if (event.target.tagName === 'A' || 
        event.target.tagName === 'BUTTON' || 
        event.target.tagName === 'INPUT' ||
        event.target.tagName === 'SELECT' ||
        event.target.tagName === 'TEXTAREA') {
        console.log('Clique ignorado - elemento interativo');
        return;
    }
    
    clickCount++;
    console.log(`Clique ${clickCount}/5 registrado`);
    
    // Limpa timer anterior
    if (clickTimer) {
        clearTimeout(clickTimer);
    }
    
    // Se atingiu 5 cliques
    if (clickCount >= 5) {
        console.log('5 cliques atingidos! Redirecionando...');
        window.location.href = '/setores';
        return;
    }
    
    // Timer de 2 segundos
    clickTimer = setTimeout(function() {
        console.log('Timer expirado - resetando contador');
        clickCount = 0;
    }, 2000);
}

// Adiciona o evento de clique
document.addEventListener('click', handleClick);

console.log('Sistema de 5 cliques simplificado ativado!'); 