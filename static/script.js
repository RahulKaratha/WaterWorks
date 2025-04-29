document.addEventListener("DOMContentLoaded", () => {
  const filterOption = document.getElementById("filterOption");
  const meterInput = document.getElementById("meterInput");
  const locationInput = document.getElementById("locationInput");
  const householdBody = document.getElementById("householdBody");

  // Toggle visibility of input fields based on selected filter option
  filterOption.addEventListener("change", () => {
    meterInput.style.display = "none";
    locationInput.style.display = "none";

    if (filterOption.value === "meter") {
      meterInput.style.display = "inline-block";
    } else if (filterOption.value === "location") {
      locationInput.style.display = "inline-block";
    }
  });

  // Fetch data based on selected filter
  window.fetchData = async function () {
    let url = "/households/";

    if (filterOption.value === "meter") {
      const meter = meterInput.value.trim();
      if (!meter) return alert("Please enter a meter number.");
      url = `/household/?meter_no=${meter}`;
    } else if (filterOption.value === "location") {
      const loc = locationInput.value;
      if (!loc) return alert("Please select a location.");
      url = `/households/${loc}`;
    }

    try {
      const response = await fetch(url);
      const data = await response.json();

      const households = Array.isArray(data) ? data : [data];
      householdBody.innerHTML = "";
      households.forEach((h) => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${h.meter_no}</td>
          <td>${h.owner_name}</td>
          <td>${h.address}</td>
          <td>${h.members_count}</td>
          <td>${h.water_allowed}</td>
          <td>${h.water_used}</td>
          <td>${h.supply_status}</td>
          <td>${h.location_name}</td>
          <td>${h.last_payment}</td>
        `;
        householdBody.appendChild(row);
      });
    } catch (error) {
      console.error("Error fetching data:", error);
      alert(
        "Failed to fetch data. Please check your input or try again later."
      );
    }
  };
});
