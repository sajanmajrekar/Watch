document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('generate-form');
    const urlInput = document.getElementById('blog-url');
    const generateBtn = document.getElementById('generate-btn');
    const btnText = form.querySelector('.btn-text');
    const btnLoader = document.getElementById('btn-loader');

    const statusContainer = document.getElementById('status-container');
    const statusBar = document.getElementById('progress-bar');
    const statusText = document.getElementById('status-text');

    const resultsContainer = document.getElementById('results-container');

    const stages = ["scraping", "extracting", "sourcing", "concepting", "processing", "compositing", "reviewing", "complete"];

    // Zoom state
    const zoomLevels = { 'compare-source': 100, 'compare-result': 100 };

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = urlInput.value.trim();
        if (!url) return;

        // Reset UI
        resultsContainer.style.display = 'none';
        btnText.style.display = 'none';
        btnLoader.style.display = 'block';
        generateBtn.disabled = true;

        statusContainer.style.display = 'block';
        statusBar.style.width = '0%';
        statusText.textContent = 'Initializing request...';

        try {
            const res = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });

            const data = await res.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // Listen to SSE
            const eventSource = new EventSource(`/stream/${data.job_id}`);

            eventSource.onmessage = (event) => {
                const msg = JSON.parse(event.data);

                if (msg.status === 'error') {
                    statusText.textContent = `Error: ${msg.data}`;
                    statusText.style.color = '#ff4d4d';
                    eventSource.close();
                    resetBtn();
                    return;
                }

                if (msg.status === 'complete') {
                    statusBar.style.width = '100%';
                    statusText.textContent = 'Cinematic Masterpiece Generated!';
                    eventSource.close();
                    showResults(msg.data);
                    resetBtn();
                    return;
                }

                // Update status text
                statusText.textContent = msg.data;
                statusText.style.color = 'var(--text-secondary)';

                // Update bar
                const idx = stages.indexOf(msg.status);
                if (idx !== -1) {
                    const pct = ((idx + 1) / (stages.length - 1)) * 100;
                    statusBar.style.width = `${pct}%`;
                }
            };

            eventSource.onerror = () => {
                eventSource.close();
                statusText.textContent = 'Connection lost.';
                resetBtn();
            };

        } catch (err) {
            statusText.textContent = `Request failed: ${err.message}`;
            statusText.style.color = '#ff4d4d';
            resetBtn();
        }
    });

    function resetBtn() {
        btnLoader.style.display = 'none';
        btnText.style.display = 'block';
        generateBtn.disabled = false;
    }

    function openCompare(sourceUrl, resultUrl) {
        const overlay = document.getElementById('compare-overlay');
        document.getElementById('compare-source').src = sourceUrl;
        document.getElementById('compare-result').src = resultUrl;
        // Reset zoom
        zoomLevels['compare-source'] = 100;
        zoomLevels['compare-result'] = 100;
        document.getElementById('compare-source').style.transform = 'scale(1)';
        document.getElementById('compare-result').style.transform = 'scale(1)';
        document.getElementById('zoom-level-source').textContent = '100%';
        document.getElementById('zoom-level-result').textContent = '100%';
        overlay.style.display = 'flex';
    }

    function showResults(data) {
        document.getElementById('res-watch').textContent = data.watch_name;
        document.getElementById('res-score').textContent = `${data.score} / 10`;

        // Azaan Kale 5 Sections
        document.getElementById('res-cd').textContent = data.creative_direction;
        document.getElementById('res-vt').textContent = data.visual_treatment;
        document.getElementById('res-fc').textContent = data.framing_composition;
        document.getElementById('res-prompt').textContent = data.ai_prompt;
        document.getElementById('res-why').textContent = data.why_it_works;

        // Review Feedback  
        document.getElementById('res-feedback').textContent = data.feedback;

        // Populate Images
        const heroImg = document.getElementById('res-img-hero');
        const heroBtn = document.getElementById('download-hero');
        heroImg.src = data.image1;
        heroBtn.href = data.image1;

        const thumbImg = document.getElementById('res-img-thumb');
        const thumbBtn = document.getElementById('download-thumb');
        thumbImg.src = data.image2;
        thumbBtn.href = data.image2;

        // Hero Compare
        document.getElementById('compare-btn-hero').onclick = () => {
            openCompare(data.source_image, data.image1);
        };

        // Thumbnail Compare
        document.getElementById('compare-btn-thumb').onclick = () => {
            openCompare(data.source_image, data.image2);
        };

        // Close
        document.getElementById('close-compare').onclick = () => {
            document.getElementById('compare-overlay').style.display = 'none';
        };

        // Zoom buttons
        document.querySelectorAll('.zoom-btn').forEach(btn => {
            btn.onclick = () => {
                const targetId = btn.dataset.target;
                const action = btn.dataset.action;
                const img = document.getElementById(targetId);

                if (action === 'in') {
                    zoomLevels[targetId] = Math.min(zoomLevels[targetId] + 25, 300);
                } else {
                    zoomLevels[targetId] = Math.max(zoomLevels[targetId] - 25, 25);
                }

                const scale = zoomLevels[targetId] / 100;
                img.style.transform = `scale(${scale})`;
                document.getElementById(`zoom-level-${targetId.split('-')[1]}`).textContent = `${zoomLevels[targetId]}%`;
            };
        });

        resultsContainer.style.display = 'flex';
        setTimeout(() => {
            resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }
});
