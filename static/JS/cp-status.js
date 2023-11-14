$(document).ready(function() {

    const ws = new WebSocket("ws://localhost:8000/cp-status-updates");
    
    ws.onopen = function() {
        console.log("Connected to the WebSocket");

        const initialLocation = localStorage.getItem('selectedLocation');
       
        if (initialLocation) {
            ws.send(JSON.stringify({ location: initialLocation}));
            localStorage.removeItem('selectedLocation');

        } else {
            console.log("No initial location set or selected");
        }
    };

    $('form').on('submit',function(event) {
        event.preventDefault();
        const location = $('#cpLocation').val();
        ws.send(JSON.stringify({ location: location}));
    })

    ws.onmessage = function(event) {
        console.log("Raw Data: ", event.data)
        const data = JSON.parse(event.data);
        console.log("parsed data: ", data);

        if (data.type == "cp_status_update") {
            const $container = $(".row");
            $container.empty(); // Clear existing cards

            data.cps_in_db.forEach(cp => {
                let statusImgSrc, statusText, opacityValue;
        
                if (cp.status=="charging") { // Convert ObjectID to string for comparison
                    statusImgSrc = "static/images/flash.png";
                    statusText = "Charging";
                    opacityValue = "1";
                } else if (cp.status=="available") {
                    statusImgSrc = "static/images/checked.png";
                    statusText = "Available";
                    opacityValue = "1";
                } else {
                    statusImgSrc = "static/images/no-wifi.png";  // Assuming you have an offline image
                    statusText = "Offline";
                    opacityValue = "0.5";  // Making it somewhat transparent
                }
        
                const cardHtml = `
                    <div class="col-lg-3 col-md-6 mb-4" style="opacity: ${opacityValue}">
                        <div class="card">
                            <div class="card-body">
                                <h5 class="card-title">Charge Point ID: ${cp._id}</h5>
                                <img class='dot' src="${statusImgSrc}" alt="">
                                <span class="status-text">${statusText}</span>
                                <img class='charger-icon' src="static/images/charger.png" alt="">
                                <a href="/metrics/${cp._id}" class="btn btn-primary">View Metrics</a>
                            </div>
                        </div>
                    </div>
                `;
        
                $container.append(cardHtml);
            });
            } else {
                console.error("cps_in_db is not an array or does not exist:", data.cps_in_db);
            }
        };
        
    

    ws.onerror = function(error) {
        console.error(`WebSocket Error: ${error}`);
    };

    ws.onclose = function(event) {
        if (event.wasClean) {
            console.log(`Closed cleanly, code=${event.code}, reason=${event.reason}`);
        } else {
            console.log("Connection died");
        }
    };
});