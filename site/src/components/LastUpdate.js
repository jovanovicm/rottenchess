import React, { useState, useEffect } from 'react';

function LastUpdate() {
  const [lastUpdate, setLastUpdate] = useState(null);

  useEffect(() => {
    const fetchLastUpdate = async () => {
      try {
        const response = await fetch('https://api.rottenchess.com/info/lastupdate');
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        const lastUpdateDate = await response.text();
        setLastUpdate(lastUpdateDate);
      } catch (error) {
        console.error('Error fetching last update:', error);
      }
    };

    fetchLastUpdate();
  }, []);

  return (
    <div className="last-update">
      {lastUpdate && <p>Last Update: {lastUpdate}</p>}
    </div>
  );
}

export default LastUpdate;