import { gql, useMutation } from "@apollo/client";
import { useState } from "react";

const CREATE_MUTATION = gql`
  mutation CreateDeal($title: String!, $amount: Float!, $currency: String!, $childCompanyId: ID!, $createdByUserId: ID!) {
    createDeal(title: $title, amount: $amount, currency: $currency, childCompanyId: $childCompanyId, createdByUserId: $createdByUserId) {
      id
      title
    }
  }
`;

const DEFAULT_USER_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"; // SALES
const DEFAULT_CHILD_COMPANY_ID = "22222222-2222-2222-2222-222222222222"; // CA child company

export default function DealCreate({ onCreated }: { onCreated: (id: string) => void }) {
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("1000");
  const [childCompanyId, setChildCompanyId] = useState(DEFAULT_CHILD_COMPANY_ID);

  const [create, { loading, error }] = useMutation(CREATE_MUTATION, {
    onCompleted: (data) => onCreated(data.createDeal.id)
  });

  return (
    <section className="bg-white border border-slate-200 rounded-lg p-4">
      <h2 className="text-base font-semibold mb-3">Create Deal</h2>
      <div className="grid gap-3">
        <input className="border px-3 py-2 rounded" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
        <input className="border px-3 py-2 rounded" placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} />
        <input className="border px-3 py-2 rounded" placeholder="Child Company ID" value={childCompanyId} onChange={(e) => setChildCompanyId(e.target.value)} />
        <button
          className="px-3 py-2 text-sm rounded bg-brand-700 text-white"
          disabled={loading}
          onClick={() =>
            create({
              variables: {
                title,
                amount: parseFloat(amount),
                currency: "CAD",
                childCompanyId,
                createdByUserId: DEFAULT_USER_ID
              }
            })
          }
        >
          {loading ? "Creating..." : "Create"}
        </button>
        {error && <div className="text-red-600 text-sm">{error.message}</div>}
      </div>
    </section>
  );
}