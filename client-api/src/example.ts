// Example usage of the Galaxy API client
import { createGalaxyApi, type HistorySummary } from "./index";

// Create a client
const api = createGalaxyApi("https://usegalaxy.org");

// Example function to get histories
async function getHistories() {
  const { data, error } = await api.GET("/api/histories");
  
  if (error) {
    console.error("Error fetching histories:", error);
    return [];
  }
  
  return data;
}

// Example function with type safety
async function getHistoryById(id: string): Promise<HistorySummary | null> {
  const { data, error } = await api.GET("/api/histories/{history_id}", {
    params: {
      path: {
        history_id: id
      }
    }
  });
  
  if (error || !data) {
    console.error("Error fetching history:", error);
    return null;
  }
  
  return data;
}

export { getHistories, getHistoryById };