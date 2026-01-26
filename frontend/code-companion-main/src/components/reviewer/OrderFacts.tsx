import { OrderFacts as OrderFactsType } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Package, Calendar, Truck } from "lucide-react";

interface OrderFactsProps {
  orderFacts: OrderFactsType;
}

export function OrderFacts({ orderFacts }: OrderFactsProps) {
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString([], {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Package className="h-4 w-4" />
          Order Details
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Order metadata */}
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div className="flex items-center gap-2">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-muted-foreground text-xs">Delivered</p>
              <p className="font-medium">{formatDate(orderFacts.delivered_at)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Truck className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-muted-foreground text-xs">Shipping</p>
              <p className="font-medium">{orderFacts.shipping_method}</p>
            </div>
          </div>
          <div>
            <p className="text-muted-foreground text-xs">Shipping Paid</p>
            <p className="font-medium">{formatCurrency(orderFacts.outbound_shipping_paid)}</p>
          </div>
        </div>

        {/* Items table */}
        <div className="border rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/50">
                <TableHead className="text-xs">SKU</TableHead>
                <TableHead className="text-xs">Product</TableHead>
                <TableHead className="text-xs text-center">Qty</TableHead>
                <TableHead className="text-xs text-right">Price</TableHead>
                <TableHead className="text-xs text-center">Warranty</TableHead>
                <TableHead className="text-xs text-center">Final Sale</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {orderFacts.items.map((item, index) => (
                <TableRow key={index}>
                  <TableCell className="font-mono text-xs">{item.sku}</TableCell>
                  <TableCell className="text-sm">{item.product.name}</TableCell>
                  <TableCell className="text-center">{item.qty}</TableCell>
                  <TableCell className="text-right">{formatCurrency(item.unit_price)}</TableCell>
                  <TableCell className="text-center">
                    <Badge variant="outline" className="text-xs">
                      {item.warranty_days}d
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    {item.is_final_sale ? (
                      <Badge variant="destructive" className="text-xs">Yes</Badge>
                    ) : (
                      <Badge variant="secondary" className="text-xs">No</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}
