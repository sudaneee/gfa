/* ==========================================================================
   FEES.JS — shared payment simulation used by the admin Payments page and
   the Parent Portal "Pay Fees" flow.
   ========================================================================== */

/**
 * Opens the payment modal (expects markup with ids: payModal, payInvoiceInfo,
 * payAmount, payMethod, payProcessBtn) and simulates a payment gateway.
 * onComplete(receipt) is called after the simulated processing finishes.
 */
function startPaymentFlow(invoiceId, onComplete) {
  const db = DB.load();
  const invoice = db.invoices.find(i => i.id === invoiceId);
  if (!invoice) { toast('Invoice not found.', 'error'); return; }
  const student = db.students.find(s => s.id === invoice.studentId);

  document.getElementById('payInvoiceInfo').innerHTML = `
    <div class="review-grid">
      <div class="item"><span class="k">Student</span><span class="v">${student ? fullName(student) : '-'}</span></div>
      <div class="item"><span class="k">Invoice No.</span><span class="v">${invoice.id}</span></div>
      <div class="item"><span class="k">Amount Due</span><span class="v">${formatCurrency(invoice.balance)}</span></div>
      <div class="item"><span class="k">Status</span><span class="v"><span class="badge badge-${statusBadgeClass(invoice.status)}">${invoice.status}</span></span></div>
    </div>`;
  document.getElementById('payAmount').value = invoice.balance;
  document.getElementById('payAmount').max = invoice.balance;
  document.getElementById('payStep1').style.display = 'block';
  document.getElementById('payStep2').style.display = 'none';
  document.getElementById('payStep3').style.display = 'none';
  document.getElementById('payModalFooter').style.display = 'flex';
  openModal('payModal');

  document.getElementById('payProcessBtn').onclick = () => {
    const amount = Number(document.getElementById('payAmount').value);
    const method = document.getElementById('payMethod').value;
    if (!amount || amount <= 0 || amount > invoice.balance) { toast('Enter a valid payment amount.', 'error'); return; }

    document.getElementById('payStep1').style.display = 'none';
    document.getElementById('payStep2').style.display = 'block';
    document.getElementById('payModalFooter').style.display = 'none';

    setTimeout(() => {
      const receipt = recordPayment(invoiceId, amount, method);
      document.getElementById('payStep2').style.display = 'none';
      document.getElementById('payStep3').style.display = 'block';
      document.getElementById('payStep3').innerHTML = `
        <div class="success-panel">
          <div class="check-circle"><i class="fa-solid fa-check"></i></div>
          <h3>Payment Successful</h3>
          <p class="text-muted">Your payment of <strong>${formatCurrency(amount)}</strong> via ${method} was processed successfully.</p>
          <div class="ref-number" style="font-size:1.1rem;padding:10px 20px;">${receipt.receiptNo}</div>
          <div class="flex gap-12 flex-center flex-wrap no-print">
            <button class="btn btn-secondary" onclick="window.print()"><i class="fa-solid fa-print"></i> Print Receipt</button>
            <button class="btn btn-primary" onclick="closeModal('payModal');location.reload();">Done</button>
          </div>
        </div>`;
      toast('Payment successful. Receipt generated.', 'success');
      if (onComplete) onComplete(receipt);
    }, 1600);
  };
}

function recordPayment(invoiceId, amount, method) {
  let receipt;
  DB.update(db => {
    const invoice = db.invoices.find(i => i.id === invoiceId);
    invoice.paid += amount;
    invoice.balance = invoice.total - invoice.paid;
    invoice.status = invoice.balance <= 0 ? 'Paid' : 'Partial';
    const payCount = db.payments.length + 1;
    receipt = {
      id: `PAY-${String(payCount).padStart(4, '0')}`, invoiceId, studentId: invoice.studentId, amount, method,
      date: new Date().toISOString().slice(0, 10), receiptNo: `RCT-${String(1000 + payCount).padStart(5, '0')}`, status: 'Successful'
    };
    db.payments.push(receipt);
  });
  return receipt;
}

/** Shared payment modal markup — inject with document.body.insertAdjacentHTML. */
const PAYMENT_MODAL_HTML = `
<div class="modal-overlay" id="payModal">
  <div class="modal">
    <div class="modal-header"><h3>Pay Fees</h3><button class="modal-close" onclick="closeModal('payModal')">&times;</button></div>
    <div class="modal-body">
      <div id="payStep1">
        <div id="payInvoiceInfo"></div>
        <hr class="divider">
        <div class="form-group"><label>Payment Amount (₦)</label><input type="number" id="payAmount" min="1"></div>
        <div class="form-group"><label>Payment Method</label>
          <select id="payMethod"><option>Card</option><option>Bank Transfer</option><option>USSD</option></select>
        </div>
      </div>
      <div id="payStep2" style="display:none;text-align:center;padding:40px 0;">
        <div class="spinner"></div>
        <h4>Processing Payment...</h4>
        <p class="text-muted">Please wait while we confirm your transaction.</p>
      </div>
      <div id="payStep3" style="display:none;"></div>
    </div>
    <div class="modal-footer no-print" id="payModalFooter">
      <button class="btn btn-secondary" onclick="closeModal('payModal')">Cancel</button>
      <button class="btn btn-primary" id="payProcessBtn"><i class="fa-solid fa-lock"></i> Pay Now</button>
    </div>
  </div>
</div>`;
