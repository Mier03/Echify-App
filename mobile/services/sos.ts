export async function getSosStatus() {
  const res = await fetch("http://localhost:8000/sos-status");
  return await res.json();
}

export async function clearSosStatus() {
  await fetch("http://localhost:8000/sos-clear", {
    method: "POST",
  });
}