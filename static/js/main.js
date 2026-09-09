/**
 * SMART EXPENSE TRACKER - MAIN FRONTEND ENGINE
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Sidebar Toggle
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const sidebar = document.querySelector('.sidebar');
    if (mobileMenuBtn && sidebar) {
        mobileMenuBtn.addEventListener('click', () => {
            sidebar.classList.toggle('mobile-open');
        });
    }

    // 2. Modals Management
    const openModalBtns = document.querySelectorAll('[data-open-modal]');
    const closeModalBtns = document.querySelectorAll('[data-close-modal]');
    const modalOverlays = document.querySelectorAll('.modal-overlay');

    openModalBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const modalId = btn.getAttribute('data-open-modal');
            const targetModal = document.getElementById(modalId);
            if (targetModal) {
                targetModal.classList.add('active');
            }
        });
    });

    closeModalBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.modal-overlay').classList.remove('active');
        });
    });

    modalOverlays.forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    });

    // 3. Auto-Dismiss Flash Messages
    const flashAlerts = document.querySelectorAll('.alert-custom');
    if (flashAlerts.length > 0) {
        setTimeout(() => {
            flashAlerts.forEach(alert => {
                alert.style.opacity = '0';
                alert.style.transition = 'opacity 0.5s ease';
                setTimeout(() => alert.remove(), 500);
            });
        }, 5000);
    }

    // 4. Quick Natural Language Transaction Parser (Global Topbar Modal)
    const nlForm = document.getElementById('nlParseForm');
    const nlInput = document.getElementById('nlPromptInput');
    const nlResultBox = document.getElementById('nlResultBox');
    const nlConfirmBtn = document.getElementById('nlConfirmBtn');

    if (nlForm && nlInput) {
        nlForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const prompt = nlInput.value.trim();
            if (!prompt) return;

            const parseBtn = document.getElementById('nlParseSubmitBtn');
            const originalBtnText = parseBtn.innerHTML;
            parseBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Parsing...';
            parseBtn.disabled = true;

            try {
                const res = await fetch('/ai/api/parse-nl-transaction', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt })
                });
                const data = await res.json();

                if (res.ok) {
                    // Populate fields into preview
                    document.getElementById('nlAmountPreview').innerText = `$${parseFloat(data.amount || 0).toFixed(2)}`;
                    document.getElementById('nlTypePreview').innerText = (data.transaction_type || 'expense').toUpperCase();
                    document.getElementById('nlTypePreview').className = data.transaction_type === 'income' ? 'badge-custom badge-income' : 'badge-custom badge-expense';
                    document.getElementById('nlCategoryPreview').innerText = data.category_name || 'Miscellaneous';
                    document.getElementById('nlDescPreview').innerText = data.description || '';
                    document.getElementById('nlDatePreview').innerText = data.transaction_date || '';

                    // Hidden fields for real form submission
                    document.getElementById('nlAmountField').value = data.amount || 0;
                    document.getElementById('nlTypeField').value = data.transaction_type || 'expense';
                    document.getElementById('nlCategoryField').value = data.category_id || '';
                    document.getElementById('nlDescField').value = data.description || '';
                    document.getElementById('nlDateField').value = data.transaction_date || '';

                    nlResultBox.style.display = 'block';
                } else {
                    alert(data.error || 'Failed to parse natural language transaction.');
                }
            } catch (err) {
                console.error(err);
                alert('An error occurred during AI parsing.');
            } finally {
                parseBtn.innerHTML = originalBtnText;
                parseBtn.disabled = false;
            }
        });
    }

    // 5. Dynamic Category Auto-Suggest in Standard Transaction Form
    const descInput = document.getElementById('transaction_description');
    const categorySelect = document.getElementById('transaction_category_id');
    const aiCategoryBadge = document.getElementById('aiCategoryBadge');

    if (descInput && categorySelect) {
        let debounceTimer;
        descInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            const text = descInput.value.trim();
            if (text.length < 3) return;

            debounceTimer = setTimeout(async () => {
                try {
                    const res = await fetch('/transactions/api/predict-category', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ description: text })
                    });
                    const data = await res.json();
                    if (data.category_id) {
                        categorySelect.value = data.category_id;
                        if (aiCategoryBadge) {
                            aiCategoryBadge.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> AI matched: ${data.category_name}`;
                            aiCategoryBadge.style.display = 'inline-flex';
                        }
                    }
                } catch (e) {
                    console.log('Category prediction skipped:', e);
                }
            }, 400);
        });
    }
});
