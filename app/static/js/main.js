function openModal() {
  document.getElementById("uploadModal").style.display = "block";
}

function closeModal() {
  document.getElementById("uploadModal").style.display = "none";
}

window.onclick = function(event) {
  if (event.target == document.getElementById("uploadModal")) {
    closeModal();
  }
}