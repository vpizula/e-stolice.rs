(function () {
    var header = document.querySelector(".zaglavlje");
    var dugme = document.querySelector(".meni-dugme");
    var meni = document.getElementById("glavni-meni");

    function zatvoriMeni() {
        header.classList.remove("meni-otvoren");
        dugme.setAttribute("aria-expanded", "false");
    }

    dugme.addEventListener("click", function () {
        var otvoren = header.classList.toggle("meni-otvoren");
        dugme.setAttribute("aria-expanded", otvoren ? "true" : "false");
    });

    meni.addEventListener("click", function (dogadjaj) {
        if (dogadjaj.target.closest("a")) zatvoriMeni();
    });

    document.addEventListener("click", function (dogadjaj) {
        if (!header.contains(dogadjaj.target)) zatvoriMeni();
    });

    document.addEventListener("keydown", function (dogadjaj) {
        if (dogadjaj.key === "Escape") zatvoriMeni();
    });

    var smanjenPokret = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var slajdovi = Array.prototype.slice.call(document.querySelectorAll(".hero-frejm .slajd"));
    var trenutni = 0;

    function prikazi(indeks) {
        slajdovi[trenutni].classList.remove("aktivno-slajd");
        trenutni = indeks;
        slajdovi[trenutni].classList.add("aktivno-slajd");
    }

    if (!smanjenPokret && slajdovi.length > 2) {
        window.setTimeout(function () { prikazi(1); }, 2800);
        window.setTimeout(function () {
            prikazi(2);
            window.setInterval(function () {
                if (document.hidden) return;
                var naredni = trenutni + 1;
                if (naredni >= slajdovi.length) naredni = 2;
                prikazi(naredni);
            }, 6000);
        }, 5400);
    }

    var paleta = document.querySelector(".paleta-boja");
    var prikaz = document.getElementById("stolica-prikaz");
    var naziv = document.getElementById("naziv-dezena");

    paleta.addEventListener("click", function (dogadjaj) {
        var taster = dogadjaj.target.closest(".boja-btn");
        if (!taster) return;
        var src = taster.getAttribute("data-src") || "";
        if (src.indexOf("assets/images/") !== 0) return;
        prikaz.src = src;
        prikaz.alt = taster.getAttribute("data-alt") || "";
        naziv.textContent = taster.getAttribute("data-naziv") || "";
        var svi = paleta.querySelectorAll(".boja-btn");
        for (var i = 0; i < svi.length; i++) {
            svi[i].classList.remove("aktivna-boja");
            svi[i].setAttribute("aria-pressed", "false");
        }
        taster.classList.add("aktivna-boja");
        taster.setAttribute("aria-pressed", "true");
    });

    function ostatak(broj, delilac) {
        return ((broj % delilac) + delilac) % delilac;
    }

    function pokreni360(lista) {
        var koren = document.getElementById("interactive-360-viewer");
        var slika = document.getElementById("image-360-active");
        var uputstvo = document.getElementById("uputstvo-360");
        var ciste = [];
        for (var i = 0; i < lista.length; i++) {
            if (/^assets\/images\/360\/\d{2}\.jpg$/.test(lista[i])) ciste.push(lista[i]);
        }
        if (!ciste.length) return;
        slika.src = ciste[0];
        if (ciste.length < 2) {
            uputstvo.textContent = "Jedan kadar stolice. Kad dodaš 01.jpg, 02.jpg i dalje, prevlačenje je vrti u krug.";
            return;
        }
        uputstvo.textContent = "Prevuci mišem ili prstom da okreneš stolicu.";
        for (var p = 0; p < ciste.length; p++) {
            var unapred = new Image();
            unapred.src = ciste[p];
        }
        var indeks = 0;
        var aktivni = null;
        var startX = 0;
        var korak = 16;
        koren.addEventListener("pointerdown", function (dogadjaj) {
            if (dogadjaj.button !== undefined && dogadjaj.button !== 0) return;
            aktivni = dogadjaj.pointerId;
            startX = dogadjaj.clientX;
            koren.setPointerCapture(dogadjaj.pointerId);
        });
        koren.addEventListener("pointermove", function (dogadjaj) {
            if (dogadjaj.pointerId !== aktivni) return;
            dogadjaj.preventDefault();
            var skokova = Math.trunc((dogadjaj.clientX - startX) / korak);
            if (skokova === 0) return;
            indeks = ostatak(indeks - skokova, ciste.length);
            slika.src = ciste[indeks];
            startX += skokova * korak;
        }, { passive: false });
        function kraj(dogadjaj) {
            if (dogadjaj.pointerId !== aktivni) return;
            aktivni = null;
        }
        koren.addEventListener("pointerup", kraj);
        koren.addEventListener("pointercancel", kraj);
    }

    var ugradjeno = [];
    try {
        ugradjeno = JSON.parse(document.getElementById("frames-360").textContent);
    } catch (greska) {
        ugradjeno = [];
    }

    fetch("assets/images/360/frames.json")
        .then(function (odgovor) {
            if (!odgovor.ok) throw new Error("nema niza");
            return odgovor.json();
        })
        .then(function (podaci) {
            if (!podaci || !podaci.length) throw new Error("prazan niz");
            pokreni360(podaci);
        })
        .catch(function () {
            pokreni360(ugradjeno);
        });

    var video = document.getElementById("video-sklapanje");
    if (video) {
        fetch("assets/video/sklapanje.mp4", { method: "HEAD" })
            .then(function (odgovor) {
                if (!odgovor.ok) return;
                var tip = odgovor.headers.get("content-type") || "";
                if (tip.indexOf("video/") !== 0 && tip.indexOf("application/mp4") === -1) return;
                video.src = "assets/video/sklapanje.mp4";
                video.hidden = false;
            })
            .catch(function () {});
    }
}());
