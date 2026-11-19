const botones = document.querySelectorAll(".boton-descarga");
const estado = document.getElementById("estado-descarga");
const ventana = document.getElementById("aviso-descarga");
const mensaje = document.getElementById("mensaje-descarga");
let descargando = false;

for (const boton of botones) {
    boton.addEventListener("click", async () => {
        if (descargando) return;
        descargando = true;
        const textoOriginal = boton.textContent;
        for (const otro of botones) otro.disabled = true;
        boton.textContent = "Preparando " + boton.dataset.formato + "...";
        estado.textContent = "Generando el archivo. Espere un momento.";
        try {
            const respuesta = await fetch(boton.dataset.url, {cache: "no-store"});
            if (!respuesta.ok) throw new Error("Error del servidor");
            const archivo = await respuesta.blob();
            if (archivo.type !== boton.dataset.tipo || archivo.size === 0) {
                throw new Error("La respuesta no contiene el archivo esperado");
            }
            const url = URL.createObjectURL(archivo);
            const enlace = document.createElement("a");
            enlace.href = url;
            enlace.download = boton.dataset.nombre;
            document.body.appendChild(enlace);
            enlace.click();
            enlace.remove();
            setTimeout(() => URL.revokeObjectURL(url), 60000);
            estado.textContent = "Archivo listo. Se inició la descarga.";
            mensaje.textContent = "Se inició la descarga de " + boton.dataset.nombre +
                ". Revise Descargas o la ubicación configurada en su navegador. " +
                "Si aparece Guardar como, confirme para guardar.";
        } catch (error) {
            estado.textContent = "No se pudo descargar el archivo.";
            mensaje.textContent = "No se pudo obtener el reporte. Revise la conexión " +
                "y que Django esté funcionando. Intente nuevamente.";
        } finally {
            descargando = false;
            for (const otro of botones) otro.disabled = false;
            boton.textContent = textoOriginal;
        }
        ventana.showModal();
    });
}
