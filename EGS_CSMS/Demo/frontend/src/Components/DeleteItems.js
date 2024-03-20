import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Link } from 'react-router-dom'; // Assuming you're using react-router

const ItemsList = () => {
  const [items, setItems] = useState([]);

  useEffect(() => {
    // Fetch items similar to previous example
  }, []);

  const deleteItem = async (itemId) => {
    try {
      await axios.delete(`http://localhost:8000/items/${itemId}/`);
      setItems(items.filter(item => item.id !== itemId)); // Update UI
    } catch (error) {
      console.error("Could not delete the item:", error);
    }
  };

  return (
    <div>
      {/* Items list */}
      {items.map(item => (
        <div key={item.id}>
          {/* Item details */}
          <Link to={`/edit/${item.id}`}>Edit</Link>
          <button onClick={() => deleteItem(item.id)}>Delete</button>
        </div>
      ))}
    </div>
  );
}

export default ItemsList;