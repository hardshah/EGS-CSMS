import React, { useState, useEffect } from 'react';
import axios from 'axios';

const AddItem = () => {
  const [status, setStatus] = useState('');
  const [networkId, setNetworkId] = useState('');
  const [currentLoad, setCurrentLoad] = useState('');
  const [networks, setNetworks] = useState([]);

  useEffect(() => {
    const fetchNetworks = async () => {
      try {
        const response = await axios('http://localhost:8000/networks/'); // Adjust this URL to where your Django server serves the list of networks
        setNetworks(response.data);
      } catch (error) {
        console.error("Could not fetch networks:", error);
      }
    };

    fetchNetworks();
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      const response = await axios.post('http://localhost:8000/items/', {
        status,
        network: networkId,
        current_load: currentLoad,
      });
      console.log(response.data);
      // Optionally reset form or give user feedback
    } catch (error) {
      console.error("Could not save the item:", error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <label>
        Status:
        <input type="text" value={status} onChange={e => setStatus(e.target.value)} />
      </label>
      <label>
        Network:
        <select value={networkId} onChange={e => setNetworkId(e.target.value)}>
          <option value="">Select a Network</option>
          {networks.map((network) => (
            <option key={network.id} value={network.id}>
              {network.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Current Load:
        <input type="number" value={currentLoad} onChange={e => setCurrentLoad(e.target.value)} />
      </label>
      <button type="submit">Add Item</button>
    </form>
  );
}

export default AddItem;