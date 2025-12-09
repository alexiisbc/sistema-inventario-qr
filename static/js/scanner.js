let html5QrcodeScanner = null;
let continuousScanner = null;
let isProcessing = false; // "Semáforo" para no escanear doble
let tipoMovimientoActual = 'entrada';

// --- MODO CONTINUO ---

async function iniciarEscaneoContinuo(tipo) {
    tipoMovimientoActual = tipo;
    
    // 1. Configurar Modal Visualmente
    const modalHeader = document.getElementById('headerModalContinuo');
    const lista = document.getElementById('lista-escaneados');
    lista.innerHTML = ""; // Limpiar historial anterior
    
    if (tipo === 'entrada') {
        modalHeader.className = "modal-header bg-success text-white";
        modalHeader.querySelector('.modal-title').innerText = "ENTRADA CONTINUA (+1)";
    } else {
        modalHeader.className = "modal-header bg-danger text-white";
        modalHeader.querySelector('.modal-title').innerText = "SALIDA CONTINUA (-1)";
    }

    // Abrir Modal
    const modal = new bootstrap.Modal(document.getElementById('modalScanContinuo'));
    modal.show();

    // 2. Iniciar Cámara
    if (continuousScanner) { await stopScannerInstance(continuousScanner); }
    
    continuousScanner = new Html5Qrcode("reader-continuous");
    
    continuousScanner.start(
        { facingMode: "environment" }, 
        { fps: 10, qrbox: { width: 250, height: 250 }, aspectRatio: 1.0 },
        (decodedText) => {
            procesarCodigoContinuo(decodedText);
        },
        (error) => {}
    ).catch(err => alert("Error cámara: " + err));
}

// Función que envía los datos al servidor sin recargar
async function procesarCodigoContinuo(sku) {
    if (isProcessing) return; // Si ya estoy procesando uno, ignoro el resto
    
    isProcessing = true;
    console.log("Procesando SKU:", sku);

    // Feedback visual inmediato (Borde amarillo = Procesando)
    const readerDiv = document.getElementById('reader-continuous');
    readerDiv.style.border = "5px solid #ffc107"; 

    try {
        const response = await fetch('/api/movement', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sku: sku, tipo: tipoMovimientoActual })
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // ÉXITO (Borde Verde)
            readerDiv.style.border = "5px solid #28a745";
            agregarAlHistorial(data.msg, 'success');
        } else {
            // ERROR (Borde Rojo)
            readerDiv.style.border = "5px solid #dc3545";
            agregarAlHistorial(data.msg, 'danger');
        }

    } catch (error) {
        console.error("Error de red:", error);
        agregarAlHistorial("Error de conexión", 'dark');
    }

    // Pausa de 2 segundos antes de permitir el siguiente escaneo
    setTimeout(() => {
        isProcessing = false;
        readerDiv.style.border = "none"; // Quitar borde
    }, 2000); 
}

function agregarAlHistorial(mensaje, tipo) {
    const lista = document.getElementById('lista-escaneados');
    const item = document.createElement('li');
    
    // Iconos según resultado
    let icono = tipo === 'success' ? '<i class="bi bi-check-circle-fill"></i>' : '<i class="bi bi-x-circle-fill"></i>';
    
    item.className = `list-group-item list-group-item-${tipo} d-flex justify-content-between align-items-center`;
    item.innerHTML = `<span>${mensaje}</span> ${icono}`;
    
    // Insertar al principio de la lista
    lista.insertBefore(item, lista.firstChild);
}

function cerrarModalContinuo() {
    if (continuousScanner) {
        stopScannerInstance(continuousScanner).then(() => {
            continuousScanner = null;
            location.reload(); // Recargar página para actualizar la tabla de stock final
        });
    } else {
        location.reload();
    }
}


// --- MODO MANUAL (Mantenemos para compatibilidad) ---
async function startScanner(inputId, type) {
    if (typeof Html5Qrcode === "undefined") return;
    document.getElementById(`scanner-container-${type}`).style.display = "block";
    if (html5QrcodeScanner) await stopScannerInstance(html5QrcodeScanner);
    
    html5QrcodeScanner = new Html5Qrcode(`reader-${type}`);
    html5QrcodeScanner.start(
        { facingMode: "environment" }, 
        { fps: 10, qrbox: { width: 250, height: 250 } },
        (decodedText) => {
            document.getElementById(inputId).value = decodedText;
            stopScanner(type);
        }, () => {}
    );
}

function stopScanner(type) {
    if (html5QrcodeScanner) {
        stopScannerInstance(html5QrcodeScanner).then(() => {
            document.getElementById(`scanner-container-${type}`).style.display = "none";
            html5QrcodeScanner = null;
        });
    }
}

function stopScannerInstance(instance) {
    return instance.stop().then(() => instance.clear()).catch(() => {});
}