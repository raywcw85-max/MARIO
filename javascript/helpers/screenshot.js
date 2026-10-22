function getScreenshot() {
    if (typeof html2canvas === 'undefined') {
        console.warn('html2canvas 未載入，無法截圖');
        return;
    }
    html2canvas(document.getElementById('game')).then(canvas => {
        // create a link to download the image
        var link = document.createElement('a');
        link.download = 'screenshot.png';
        link.href = canvas.toDataURL('image/png').replace('image/png', 'image/octet-stream');
        link.click();
    });
}
