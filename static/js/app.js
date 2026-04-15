document.addEventListener("DOMContentLoaded", () => {
    document.body.classList.add("motion-ready");

    const currentPath = window.location.pathname.replace(/\/+$/, "") || "/";
    for (const link of document.querySelectorAll(".site-nav a")) {
        const target = new URL(link.href, window.location.origin);
        const linkPath = target.pathname.replace(/\/+$/, "") || "/";
        if (linkPath === currentPath) {
            link.classList.add("is-active");
        }
    }

    const revealTargets = Array.from(
        document.querySelectorAll(
            ".panel, .feature-card, .flash-item, .service-card, .schedule-card, .news-message"
        )
    );

    revealTargets.forEach((element, index) => {
        element.classList.add("reveal-item");
        element.style.setProperty("--reveal-delay", `${Math.min(index * 45, 260)}ms`);
    });

    if (!("IntersectionObserver" in window)) {
        for (const element of revealTargets) {
            element.classList.add("is-visible", "is-static");
        }
    } else {
        const observer = new IntersectionObserver(
            (entries) => {
                for (const entry of entries) {
                    if (!entry.isIntersecting) {
                        continue;
                    }

                    entry.target.classList.add("is-visible");
                    observer.unobserve(entry.target);
                }
            },
            {
                threshold: 0.16,
                rootMargin: "0px 0px -40px 0px",
            }
        );

        for (const element of revealTargets) {
            observer.observe(element);
        }
    }

    for (const element of document.querySelectorAll(".panel, .feature-card, .service-card, .schedule-card")) {
        element.addEventListener("pointermove", (event) => {
            const bounds = element.getBoundingClientRect();
            const offsetX = ((event.clientX - bounds.left) / bounds.width) * 100;
            const offsetY = ((event.clientY - bounds.top) / bounds.height) * 100;
            element.style.setProperty("--pointer-x", `${offsetX}%`);
            element.style.setProperty("--pointer-y", `${offsetY}%`);
        });
    }
});
