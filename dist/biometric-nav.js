
(function () {
    function initBiometricNavigation() {
        const section = document.getElementById("biometric");
        const dock = document.querySelector(".journey-dock");

        if (!section || !dock) return;

        const observer = new IntersectionObserver(
            function (entries) {
                document.body.classList.toggle(
                    "biometric-in-view",
                    entries[0].isIntersecting
                );
            },
            {
                root: null,
                threshold: 0,
                rootMargin: "0px 0px -48px 0px"
            }
        );

        observer.observe(section);
    }

    if (document.readyState === "loading") {
        document.addEventListener(
            "DOMContentLoaded",
            initBiometricNavigation
        );
    } else {
        initBiometricNavigation();
    }
})();
