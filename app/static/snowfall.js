
document.addEventListener("DOMContentLoaded", () => {
    // Snowfall is enabled only on devices with a mouse or trackpad.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        return;
    }

    let lastSpawn = 0;

    document.addEventListener("mousemove", (event) => {
        const now = performance.now();

        // Limit particle creation for smoother performance.
        if (now - lastSpawn < 35) return;
        lastSpawn = now;

        const flake = document.createElement("span");
        flake.className = "cursor-snowflake";
        flake.textContent = ["❄", "❅", "❆", "✧"][
            Math.floor(Math.random() * 4)
        ];

        const size = 8 + Math.random() * 13;

        flake.style.left =
            `${event.clientX + (Math.random() - 0.5) * 24}px`;

        flake.style.top =
            `${event.clientY + (Math.random() - 0.5) * 18}px`;

        flake.style.fontSize = `${size}px`;
        flake.style.setProperty(
            "--snow-drift",
            `${(Math.random() - 0.5) * 90}px`
        );

        document.body.appendChild(flake);

        // Automatically remove old particles.
        flake.addEventListener("animationend", () => flake.remove());
    });
});
