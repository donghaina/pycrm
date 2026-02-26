import React from "react";
import ReactDOM from "react-dom/client";
import { ApolloClient, ApolloProvider, HttpLink, InMemoryCache } from "@apollo/client";
import App from "./ui/App";
import "./styles.css";

const client = new ApolloClient({
  link: new HttpLink({
    uri: import.meta.env.VITE_GATEWAY_URL || "http://localhost:4000/graphql",
    headers: { "x-user-id": "u1" }
  }),
  cache: new InMemoryCache()
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ApolloProvider client={client}>
      <App />
    </ApolloProvider>
  </React.StrictMode>
);
