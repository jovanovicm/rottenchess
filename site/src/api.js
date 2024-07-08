export const fetchPlayersList = async () => {
    try {
      const response = await fetch("https://api.rottenchess.com/players");
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return await response.json();
    } catch (error) {
      console.error("Error fetching players list:", error);
      return null;
    }
  };
  
  export const fetchPlayersBatch = async (usernames) => {
    try {
      const response = await fetch("https://api.rottenchess.com/players/batch", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ usernames }),
      });
      if (!response.ok) {
        throw new Error("Network response was not ok");
      }
      return await response.json();
    } catch (error) {
      console.error("Error fetching players batch:", error);
      return null;
    }
  };