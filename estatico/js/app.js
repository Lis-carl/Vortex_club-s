/* JavaScript mínimo, sin librerías: votos/reacciones sin recargar, chat con consulta periódica y confirmaciones. */
(function () {
  "use strict";

  // Confirmaciones y envío por fetch (votos y reacciones).
  document.addEventListener("submit", function (e) {
    var f = e.target;
    var boton = e.submitter;
    var texto = (boton && boton.getAttribute("data-confirmar-boton")) || f.getAttribute("data-confirmar");
    if (texto && !window.confirm(texto)) { e.preventDefault(); return; }

    if (f.hasAttribute("data-chat-form")) { e.preventDefault(); enviarChat(f); return; }

    var destino = f.getAttribute("data-ajax");
    if (!destino || !window.fetch) { return; }
    e.preventDefault();
    fetch(f.action, {
      method: "POST", credentials: "same-origin",
      headers: { "X-Requested-With": "fetch", "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(new FormData(f))
    }).then(function (r) { return r.json(); }).then(function (datos) {
      var elemento = document.getElementById(destino);
      if (elemento && datos.html) { elemento.outerHTML = datos.html; }
    }).catch(function () { f.submit(); });
  });

  // Mostrar u ocultar contraseña.
  document.addEventListener("click", function (e) {
    if (e.target.hasAttribute("data-ver-contrasena")) {
      var campo = e.target.parentNode.querySelector("input");
      campo.type = campo.type === "password" ? "text" : "password";
    }
  });

  // Chat del club.
  var chat = document.getElementById("chat");
  if (!chat) { return; }
  var lista = document.getElementById("mensajes");
  var ultimo = parseInt(chat.getAttribute("data-ultimo") || "0", 10);
  var url = chat.getAttribute("data-url");
  lista.scrollTop = lista.scrollHeight;

  function pintar(m) {
    var vacio = document.getElementById("sin-mensajes");
    if (vacio) { vacio.remove(); }
    var caja = document.createElement("div");
    caja.className = "mensaje" + (m.mio ? " mio" : "");
    var cabecera = document.createElement("small");
    var negrita = document.createElement("b");
    negrita.textContent = m.autor;          // textContent: el texto del usuario nunca se interpreta como HTML
    cabecera.appendChild(negrita);
    cabecera.appendChild(document.createTextNode(" · " + m.hora));
    var parrafo = document.createElement("p");
    parrafo.textContent = m.contenido;
    caja.appendChild(cabecera);
    caja.appendChild(parrafo);
    lista.appendChild(caja);
  }

  function consultar() {
    fetch(url + "/mensajes?desde=" + ultimo, { credentials: "same-origin", headers: { "X-Requested-With": "fetch" } })
      .then(function (r) { return r.json(); })
      .then(function (mensajes) {
        if (!Array.isArray(mensajes) || !mensajes.length) { return; }
        var alFinal = lista.scrollTop + lista.clientHeight >= lista.scrollHeight - 40;
        mensajes.forEach(function (m) { pintar(m); ultimo = Math.max(ultimo, m.id); });
        if (alFinal) { lista.scrollTop = lista.scrollHeight; }
      }).catch(function () { /* se reintenta en el siguiente ciclo */ });
  }

  function enviarChat(f) {
    var campo = f.querySelector("input[name=contenido]");
    if (!campo.value.trim()) { return; }
    fetch(f.action, {
      method: "POST", credentials: "same-origin",
      headers: { "X-Requested-With": "fetch", "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams(new FormData(f))
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d.ok) { campo.value = ""; consultar(); lista.scrollTop = lista.scrollHeight; }
    }).catch(function () { f.submit(); });
  }

  window.setInterval(consultar, 3000);
}());
