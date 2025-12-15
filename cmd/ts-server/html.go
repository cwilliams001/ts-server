package main

const uploadPageHTML = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>TS File Server</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
  <style>
    :root {
      --bg-color: #121212;
      --container-bg: #1e1e1e;
      --text-color: #e0e0e0;
      --border-color: #333333;
      --hover-color: #2c2c2c;
      --button-bg: #6200ea;
      --button-hover: #3700b3;
      --copy-button-bg: #03dac6;
      --copy-button-hover: #018786;
      --download-button-bg: #03a9f4;
      --download-button-hover: #0288d1;
      --drop-zone-bg: #2c2c2c;
    }
    body {
      background-color: var(--bg-color);
      color: var(--text-color);
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 0;
    }
    .container {
      max-width: 800px;
      margin: 40px auto;
      background-color: var(--container-bg);
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 2px 10px rgba(0,0,0,0.5);
    }
    h1, h2 {
      text-align: center;
      margin-bottom: 20px;
    }
    .instructions {
      margin-bottom: 30px;
      padding: 15px;
      background-color: var(--hover-color);
      border: 1px solid var(--border-color);
      border-radius: 8px;
    }
    .instructions pre {
      background: #1e1e1e;
      padding: 10px;
      border-radius: 4px;
      overflow-x: auto;
      margin: 10px 0;
    }
    .instructions p {
      font-size: 14px;
      line-height: 1.4;
    }
    .upload-section {
      margin-bottom: 30px;
      padding: 20px;
      border: 2px dashed var(--border-color);
      border-radius: 8px;
      text-align: center;
      transition: background-color 0.3s ease;
    }
    .upload-section:hover {
      background-color: var(--hover-color);
    }
    #drop-zone {
      padding: 40px;
      border: 2px dashed var(--border-color);
      border-radius: 8px;
      background-color: var(--drop-zone-bg);
      cursor: pointer;
      transition: background-color 0.3s ease;
    }
    #drop-zone.dragover {
      background-color: var(--hover-color);
    }
    .upload-button {
      background-color: var(--button-bg);
      color: #ffffff;
      padding: 10px 20px;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      margin-top: 20px;
      font-size: 16px;
      transition: background-color 0.3s ease;
    }
    .upload-button:hover {
      background-color: var(--button-hover);
    }
    #selected-files {
      margin-top: 10px;
      font-size: 14px;
      text-align: left;
    }
    #selected-files ul {
      list-style-type: none;
      padding-left: 0;
      margin: 0;
    }
    #selected-files li {
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .file-list {
      margin-top: 30px;
    }
    .file-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px;
      border-bottom: 1px solid var(--border-color);
    }
    .file-info {
      flex: 1;
      margin-right: 10px;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
    }
    .file-info a {
      color: var(--button-bg);
      text-decoration: none;
    }
    .file-info a:hover {
      text-decoration: underline;
    }
    .button-group {
      display: flex;
      gap: 5px;
      flex-shrink: 0;
    }
    .copy-button {
      background-color: var(--copy-button-bg);
      color: #000000;
      border: none;
      padding: 5px 10px;
      border-radius: 4px;
      cursor: pointer;
      transition: background-color 0.3s ease;
    }
    .copy-button:hover {
      background-color: var(--copy-button-hover);
    }
    .download-button {
      background-color: var(--download-button-bg);
      color: #000000;
      border: none;
      padding: 5px 10px;
      border-radius: 4px;
      cursor: pointer;
      transition: background-color 0.3s ease;
      text-decoration: none;
      display: inline-block;
    }
    .download-button:hover {
      background-color: var(--download-button-hover);
    }
    #upload-progress {
      display: none;
      margin-top: 10px;
    }
    .progress-bar {
      width: 100%;
      height: 20px;
      background-color: var(--border-color);
      border-radius: 10px;
      overflow: hidden;
    }
    .progress {
      width: 0%;
      height: 100%;
      background-color: var(--button-bg);
      transition: width 0.3s ease;
    }
    .message {
      margin-top: 10px;
      font-size: 14px;
    }
    .error {
      color: #ff6b6b;
    }
    .success {
      color: #4caf50;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>TS File Server</h1>
    <div class="instructions">
      <h2>Usage Instructions</h2>
      <p><strong>1. Upload a file via the HTML interface:</strong><br>
         Drag and drop your file(s) into the upload area below and click "Upload Files".</p>
      <p><strong>2. Upload a file via <code>curl</code>:</strong></p>
      <pre>curl -X POST -F "file=@/path/to/your/file.txt" https://&lt;your-url&gt;/</pre>
      <p><strong>3. Download a file:</strong><br>
         <em>From the browser:</em> Click the file link or the <strong>Download</strong> button.<br>
         <em>From the command line:</em></p>
      <pre>curl https://&lt;your-url&gt;/file.txt -O</pre>
    </div>
    <div class="upload-section">
      <h2>Upload Files</h2>
      <form id="upload-form" enctype="multipart/form-data" method="post">
        <div id="drop-zone">
          <i class="fas fa-cloud-upload-alt" style="font-size: 48px;"></i>
          <p>Drag & drop files here or click to select</p>
          <input type="file" name="file" multiple style="display: none;" id="file-input">
        </div>
        <div id="selected-files"></div>
        <div id="upload-progress">
          <div class="progress-bar">
            <div class="progress"></div>
          </div>
          <div id="progress-text">0%</div>
        </div>
        <div id="status-message" class="message"></div>
        <button type="submit" class="upload-button">Upload Files</button>
      </form>
    </div>
    <div class="file-list">
      <h2>Available Files</h2>
      <div id="files">
        <!-- File list will load here -->
      </div>
    </div>
  </div>
  <script>
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const selectedFilesDiv = document.getElementById('selected-files');
    const uploadForm = document.getElementById('upload-form');
    const progressBar = document.querySelector('.progress');
    const progressText = document.getElementById('progress-text');
    const uploadProgress = document.getElementById('upload-progress');
    const statusMessage = document.getElementById('status-message');

    dropZone.onclick = () => fileInput.click();

    function updateSelectedFiles() {
      const files = fileInput.files;
      if (files.length > 0) {
        let fileListHTML = '<ul>';
        for (let i = 0; i < files.length; i++) {
          fileListHTML += ` + "`<li>${files[i].name} (${formatFileSize(files[i].size)})</li>`" + `;
        }
        fileListHTML += '</ul>';
        selectedFilesDiv.innerHTML = fileListHTML;
      } else {
        selectedFilesDiv.innerHTML = '';
      }
    }

    fileInput.addEventListener('change', updateSelectedFiles);

    dropZone.ondragover = (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    };
    dropZone.ondragleave = () => {
      dropZone.classList.remove('dragover');
    };
    dropZone.ondrop = (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
      fileInput.files = e.dataTransfer.files;
      updateSelectedFiles();
    };

    uploadForm.onsubmit = async (e) => {
      e.preventDefault();
      const formData = new FormData(uploadForm);
      uploadProgress.style.display = 'block';
      statusMessage.textContent = '';
      try {
        const xhr = new XMLHttpRequest();
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percent = (event.loaded / event.total) * 100;
            progressBar.style.width = percent + '%';
            progressText.textContent = Math.round(percent) + '%';
          }
        };
        xhr.onload = function() {
          if (xhr.status === 200) {
            statusMessage.className = 'message success';
            statusMessage.textContent = 'Files uploaded successfully!';
            loadFiles();
            uploadForm.reset();
            updateSelectedFiles();
            progressBar.style.width = '0%';
            progressText.textContent = '0%';
          } else {
            statusMessage.className = 'message error';
            statusMessage.textContent = 'Upload failed!';
          }
          uploadProgress.style.display = 'none';
        };
        xhr.onerror = function() {
          statusMessage.className = 'message error';
          statusMessage.textContent = 'Upload failed!';
          uploadProgress.style.display = 'none';
        };
        xhr.open('POST', '/');
        xhr.send(formData);
      } catch (error) {
        statusMessage.className = 'message error';
        statusMessage.textContent = 'Upload failed: ' + error;
        uploadProgress.style.display = 'none';
      }
    };

    function formatFileSize(bytes) {
      const units = ['B', 'KB', 'MB', 'GB', 'TB'];
      let size = bytes;
      let unitIndex = 0;
      while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
      }
      return ` + "`${size.toFixed(1)} ${units[unitIndex]}`" + `;
    }

    async function loadFiles() {
      try {
        const response = await fetch('/list');
        const files = await response.json();
        const filesDiv = document.getElementById('files');
        filesDiv.innerHTML = '';
        files.forEach(file => {
          const fileDiv = document.createElement('div');
          fileDiv.className = 'file-item';

          const fileInfo = document.createElement('div');
          fileInfo.className = 'file-info';
          const fileLink = document.createElement('a');
          fileLink.href = '/' + file.name;
          fileLink.textContent = ` + "`${file.name} (${formatFileSize(file.size)})`" + `;
          fileInfo.appendChild(fileLink);

          const buttonGroup = document.createElement('div');
          buttonGroup.className = 'button-group';

          const copyButton = document.createElement('button');
          copyButton.className = 'copy-button';
          copyButton.innerHTML = '<i class="fas fa-copy"></i>';
          copyButton.onclick = (e) => {
            e.preventDefault();
            navigator.clipboard.writeText(window.location.origin + '/' + file.name);
            copyButton.innerHTML = '<i class="fas fa-check"></i>';
            setTimeout(() => {
              copyButton.innerHTML = '<i class="fas fa-copy"></i>';
            }, 2000);
          };

          const downloadButton = document.createElement('a');
          downloadButton.className = 'download-button';
          downloadButton.href = '/' + file.name;
          downloadButton.setAttribute('download', '');
          downloadButton.innerHTML = '<i class="fas fa-download"></i>';

          buttonGroup.appendChild(copyButton);
          buttonGroup.appendChild(downloadButton);

          fileDiv.appendChild(fileInfo);
          fileDiv.appendChild(buttonGroup);
          filesDiv.appendChild(fileDiv);
        });
      } catch (error) {
        console.error('Error loading files:', error);
      }
    }
    loadFiles();
  </script>
</body>
</html>
`
