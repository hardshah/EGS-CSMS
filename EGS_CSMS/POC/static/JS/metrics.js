document.addEventListener("DOMContentLoaded", function() {

    const cp_id = document.body.getAttribute('data-cp-id');

    const socket = new WebSocket(`ws://localhost:8000/ws/${cp_id}`);

    socket.onopen = function() {
        console.log("WebSocket Connection opened for CP:", cp_id);
    };

    socket.onmessage = function(event) {
        const data = JSON.parse(event.data);

        //Update metrics
        if (data.type === 'update' && data.cp_data) {
            const metricsList = document.querySelector('.list-group.list-group-flush');
            // clear the previous metrics
            metricsList.innerHTML = "";

            for (const [metric, value] of Object.entries(data.cp_data)) {
                const listItem = document.createElement('li');
                listItem.className = "list-group-item d-flex justify-content-between align-items-center";
                listItem.innerHTML = `<strong class="measurand-text">${metric}</strong><span>${value}</span>`;
                metricsList.appendChild(listItem);
            }
        }

        //update logs
        if (data.type === 'update' && data.logs) {
            const logConsole = document.querySelector('.log-console');
            logConsole.innerHTML = `<div class='card-header'><h4>Logs for Charge Point ${cp_id}</h4></div>`; // clear and add header

            data.logs.forEach(log => {
                const logEntry = document.createElement('p');
                logEntry.innerHTML = `<span class="log-timestamp">${log.timestamp}</span>: ${log.message}`;
                logConsole.appendChild(logEntry);
            });
        }
    };

    socket.onclose = function(event) {
        if (event.wasClean) {
            console.log(`WebSocket Connection for CP:${cp_id} closed cleanly, code=${event.code}, reason=${event.reason}`);
        } else {
            console.error('WebSocket Connection for CP:', cp_id, 'died');
        }
    };

    socket.onerror = function(error) {
        console.error(`WebSocket Error for CP:${cp_id}:`, error);
    };
});