import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useParams, useNavigate } from 'react-router-dom';

const EditItem = () => {
  const [status, setStatus] = useState('');
  const [networkId, setNetworkId] = useState('');
  const [currentLoad, setCurrentLoad] = useState('');
  const [networks, setNetworks] = useState([]);
  const { itemId } = useParams(); // Assuming you're using react-router for routing
  const navigate = useNavigate();

  useEffect(() => {
    const fetchNetworks = async () => {
      try {
        const networksResponse = await axios('http://localhost:8000/networks/');
        setNetworks(networksResponse.data);
      } catch (error) {
        console.error("Could not fetch networks:", error);
      }
    };

    const fetchItem = async () => {
      try {
        const itemResponse = await axios(`http://localhost:8000/items/${itemId}/`);
        const { status, network, current_load } = itemResponse.data;
        setStatus(status);
        setNetworkId(network);
        setCurrentLoad(current_load);
      } catch (error) {
        console.error("Could not fetch item data:", error);
      }
    };

    fetchNetworks();
    fetchItem();
  }, [itemId]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    try {
      await axios.put(`http://localhost:8000/items/${itemId}/`, {
        status,
        network: networkId,
        current_load: currentLoad,
      });
      navigate('/items'); // Redirect back to the items listing, adjust URL as needed
    } catch (error) {
      console.error("Could not update the item:", error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Form fields here, similar to the AddItem component */}
    </form>
  );
}

export default EditItem;