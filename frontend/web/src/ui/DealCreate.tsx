import { gql, useMutation, useQuery } from "@apollo/client";
import { useEffect, useMemo, useState } from "react";

type CompanyOption = {
  id: string;
  name: string;
};

const CREATE_MUTATION = gql`
  mutation CreateDeal($title: String!, $amount: Float!, $currency: String!, $childCompanyId: ID!, $createdByUserId: ID!) {
    createDeal(title: $title, amount: $amount, currency: $currency, childCompanyId: $childCompanyId, createdByUserId: $createdByUserId) {
      id
      title
    }
  }
`;

const DEFAULT_USER_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"; // SALES

const ME_QUERY = gql`
  query Me {
    me {
      id
      role
      companyId
    }
  }
`;

const COMPANY_AND_CHILDREN_QUERY = gql`
  query CompanyAndChildren($parentId: ID!) {
    company(id: $parentId) {
      id
      name
      parentId
    }
    childCompanies(parentId: $parentId) {
      id
      name
    }
  }
`;

export default function DealCreate({ onCreated }: { onCreated: (id: string) => void }) {
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("1000");
  const [childCompanyId, setChildCompanyId] = useState("");

  const { data: meData, loading: meLoading, error: meError } = useQuery(ME_QUERY);
  const me = meData?.me;

  const {
    data: companyData,
    loading: companyLoading,
    error: companyError
  } = useQuery(COMPANY_AND_CHILDREN_QUERY, {
    variables: { parentId: me?.companyId },
    skip: !me?.companyId
  });

  const options = useMemo<CompanyOption[]>(() => {
    if (!companyData) return [];
    const children = companyData.childCompanies ?? [];
    if (children.length > 0) return children;
    const own = companyData.company;
    return own ? [own] : [];
  }, [companyData]);

  useEffect(() => {
    if (!options.length) return;
    if (!childCompanyId || !options.find((o) => o.id === childCompanyId)) {
      setChildCompanyId(options[0].id);
    }
  }, [options, childCompanyId]);

  const [create, { loading, error }] = useMutation(CREATE_MUTATION, {
    onCompleted: (data) => {
      onCreated(data.createDeal.id);
      setTitle("");
      setAmount("1000");
    }
  });

  const loadingCompanies = meLoading || companyLoading;
  const companyErrorMessage = meError?.message || companyError?.message;

  return (
    <section className="bg-white border border-slate-200 rounded-lg p-4">
      <h2 className="text-base font-semibold mb-3">Create Deal</h2>
      <div className="grid gap-3">
        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600 w-32">Title</label>
          <input className="border px-3 py-2 rounded flex-1" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600 w-32">Amount</label>
          <input className="border px-3 py-2 rounded flex-1" placeholder="Amount" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </div>
        <div className="flex items-center gap-3">
          <label className="text-sm text-slate-600 w-32">Child Company</label>
          <select
            className="border px-3 py-2 rounded flex-1"
            value={childCompanyId}
            onChange={(e) => setChildCompanyId(e.target.value)}
            disabled={loadingCompanies || options.length === 0}
          >
            {loadingCompanies && <option>Loading companies...</option>}
            {!loadingCompanies && options.length === 0 && <option>No available companies</option>}
            {!loadingCompanies && options.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name} ({company.id})
              </option>
            ))}
          </select>
        </div>
        <button
          className="px-3 py-2 text-sm rounded bg-brand-700 text-white w-fit justify-self-start"
          disabled={loading || !childCompanyId}
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
        {companyErrorMessage && <div className="text-red-600 text-sm">{companyErrorMessage}</div>}
        {error && <div className="text-red-600 text-sm">{error.message}</div>}
      </div>
    </section>
  );
}
