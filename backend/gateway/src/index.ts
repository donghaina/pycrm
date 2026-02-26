import { ApolloServer } from "@apollo/server";
import { startStandaloneServer } from "@apollo/server/standalone";
import {
  ApolloGateway,
  IntrospectAndCompose,
  RemoteGraphQLDataSource,
} from "@apollo/gateway";

const orgUrl = process.env.ORG_SUBGRAPH_URL || "http://org-service:4001/graphql";
const crmUrl = process.env.CRM_SUBGRAPH_URL || "http://crm-service:4002/graphql";

const gateway = new ApolloGateway({
  supergraphSdl: new IntrospectAndCompose({
    subgraphs: [
      { name: "org", url: orgUrl },
      { name: "crm", url: crmUrl },
    ],
  }),

  // ✅ 关键：透传自定义 header 给下游 subgraphs
  buildService({ url }) {
    return new RemoteGraphQLDataSource({
      url,
      willSendRequest({ request, context }) {
        const userId = context?.userId;
        if (userId) {
          request.http?.headers.set("x-user-id", userId);
        }
      },
    });
  },
});

const server = new ApolloServer({ gateway });

startStandaloneServer(server, {
  listen: { port: 4000 },

  // ✅ 关键：从客户端请求读取 x-user-id，放到 context 里给 buildService 用
  context: async ({ req }) => {
    const userId = req.headers["x-user-id"];
    // req.headers 可能是 string | string[] | undefined，这里只取 string
    return { userId: Array.isArray(userId) ? userId[0] : userId };
  },
}).then(({ url }) => {
  console.log(`Gateway ready at ${url}`);
});