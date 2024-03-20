import React, { useState, useEffect } from 'react';
import axios from 'axios';

const ItemsList = () => {
  const [items, setItems] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      const result = await axios(
        'http://localhost:8000/items/', // Adjust this URL to where your Django server is running
      );
      setItems(result.data);
    };

    fetchData();
  }, []);

  return (
    <ul>
      {items.map(item => (
        <li key={item.id}>
          Status: {item.status}, Network ID: {item.network}, Current Load: {item.current_load}
        </li>
      ))}
    </ul>
  );
}

export default ItemsList;