import React, { useEffect, useState } from 'react';
import axios from 'axios';

function App() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    axios.get('http://localhost:8000/api/items/')
      .then(response => {
        setItems(response.data);
      });
  }, []);

  return (
    <div>
      <h1>Items</h1>
      {items.map(item => (
  <div key={item.id}>
    <h2>Network ID: {item.network_id}</h2>
    <p>Status: {item.status}</p>
    <p>Current Load: {item.current_load}</p>
  </div>
))}
    </div>
  );
}

export default App;