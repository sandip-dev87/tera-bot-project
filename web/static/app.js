// Auto refresh dashboard har 30 sec
if (window.location.pathname === "/dashboard") {
    setTimeout(() => {
        window.location.reload();
    }, 30000);
}

// Confirm delete buttons
document.querySelectorAll('form').forEach(form => {
    const btn = form.querySelector('button');
    if (btn && (btn.textContent.includes('Delete') || btn.textContent.includes('Reject'))) {
        form.addEventListener('submit', (e) => {
            if (!confirm('Pakka? Ye action undo nahi hoga.')) {
                e.preventDefault();
            }
        });
    }
});

// Copy URL helper
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert('Copied!');
    });
}

// Format currency
function formatCurrency(amount) {
    return '₹' + Number(amount).toLocaleString('en-IN');
}

console.log('Admin panel loaded ✅');
