function expand(el) {
    let details = el.closest("div").querySelector(".details")
    if (details.style.display === "block") {
        details.style.display = "none"
        el.innerHTML = "+"
    } else {
        details.style.display = "block"
        el.innerHTML = "-"
    }
}