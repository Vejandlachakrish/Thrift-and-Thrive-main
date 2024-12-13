function filterItems() {
    let input = document.getElementById('search-bar').value.toLowerCase();
    let items = document.querySelectorAll('.item-card');

    items.forEach(item => {
        let itemName = item.querySelector('h2').innerText.toLowerCase();
        if (itemName.includes(input)) {
            item.style.display = '';
        } else {
            item.style.display = 'none';
        }
    });
}