function expand(el, cls) {
    let details = el.closest("div").querySelector("." + cls)
    if (details.style.display === "block") {
        details.style.display = "none"
        el.innerHTML = "+"
    } else {
        details.style.display = "block"
        el.innerHTML = "-"
    }
}