
// Function to add copy buttons to code blocks
function addCopyButtons() {
    document.querySelectorAll('.highlight pre').forEach(function(preElement) {
        // Prevent adding a button if one already exists
        if (preElement.querySelector('.copy-code-button')) {
            return;
        }

        var button = document.createElement('button');
        button.className = 'copy-code-button';
        button.type = 'button';
        button.innerText = 'Copy';

        preElement.style.position = 'relative';
        preElement.appendChild(button);

        button.addEventListener('click', function() {
            var textToCopy = preElement.innerText;
            navigator.clipboard.writeText(textToCopy).then(function() {
                button.innerText = 'Copied!';
                setTimeout(function() {
                    button.innerText = 'Copy';
                }, 2000);
            }).catch(function(err) {
                console.error('Failed to copy text: ', err);
                button.innerText = 'Error!';
                setTimeout(function() {
                    button.innerText = 'Copy';
                }, 2000);
            });
        });
    });
}

// Observe changes in the chat history and add copy buttons to new code blocks
const observer = new MutationObserver(function(mutations) {
    mutations.forEach(function(mutation) {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
            addCopyButtons();
        }
    });
});

// Start observing the chat history container
// We need to wait for the container to exist
window.addEventListener('load', () => {
    const targetNode = document.getElementById('chat-history');
    if (targetNode) {
        observer.observe(targetNode, { childList: true, subtree: true });
        // Initial run
        addCopyButtons();
    }
});
