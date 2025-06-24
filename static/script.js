document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.querySelector('form');
    const uploadButton = uploadForm.querySelector('button[type="submit"]');
    const fileInput = uploadForm.querySelector('input[type="file"]');
    const container = document.querySelector('.container'); // Get the main container

    if (uploadForm && uploadButton && fileInput && container) {
        uploadForm.addEventListener('submit', function() {
            // Check if a file is actually selected before showing loading
            if (fileInput.files.length > 0) {
                // Sembunyikan form dan tampilkan pesan loading
                uploadForm.style.display = 'none';

                // Buat elemen loading
                const loadingDiv = document.createElement('div');
                loadingDiv.className = 'loading-spinner'; // Class for styling
                loadingDiv.innerHTML = `
                    <div class="spinner"></div>
                    <p>Processing video, please wait...</p>
                    <p class="note">This may take a few moments depending on video length and size.</p>
                `;
                container.appendChild(loadingDiv); // Add to container

                // Opsional: disable tombol submit untuk mencegah pengiriman ganda
                uploadButton.disabled = true;
                uploadButton.textContent = 'Processing...';
            }
        });
    }
});