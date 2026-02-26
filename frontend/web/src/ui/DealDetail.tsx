import { gql, useMutation, useQuery } from "@apollo/client";

const DEAL_QUERY = gql`
  query Deal($id: ID!) {
    deal(id: $id) {
      id
      title
      amount
      currency
      reviewStatus
      reviewReason
    }
  }
`;

const SUBMIT_MUTATION = gql`
  mutation Submit($dealId: ID!) {
    submitDealForReview(dealId: $dealId) {
      id
      reviewStatus
    }
  }
`;

export default function DealDetail({ id }: { id: string }) {
  const { data, loading, error, startPolling, stopPolling } = useQuery(DEAL_QUERY, {
    variables: { id },
    pollInterval: 0
  });

  const [submit] = useMutation(SUBMIT_MUTATION, {
    variables: { dealId: id },
    onCompleted: () => startPolling(2000),
    onError: () => stopPolling()
  });

  if (loading) return <div>Loading deal...</div>;
  if (error) return <div className="text-red-600">{error.message}</div>;

  const deal = data?.deal;
  if (!deal) return <div>No deal found.</div>;

  return (
    <section className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold">Deal Detail</h2>
        <button
          className="px-3 py-1 text-sm rounded bg-brand-500 text-white"
          onClick={() => submit()}
        >
          Submit for Review
        </button>
      </div>
      <div className="mt-3 text-sm space-y-1">
        <div><span className="text-slate-500">Title:</span> {deal.title}</div>
        <div><span className="text-slate-500">Amount:</span> {deal.amount} {deal.currency}</div>
        <div><span className="text-slate-500">Status:</span> {deal.reviewStatus}</div>
        {deal.reviewReason && <div><span className="text-slate-500">Reason:</span> {deal.reviewReason}</div>}
      </div>
    </section>
  );
}
