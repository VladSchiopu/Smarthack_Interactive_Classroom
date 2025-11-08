async function sendToServer() {
    const text = document.getElementById("userInput").value;
    const output = document.getElementById("modelResponse");

    output.textContent = "Se procesează...";

    try {
        const response = await fetch("/api/query", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: text })
        });

        const data = await response.json();

        // Afișăm doar răspunsul modelului
        output.textContent = data.response;

    } catch (err) {
        output.textContent = "Eroare la apel: " + err.message;
    }
}
